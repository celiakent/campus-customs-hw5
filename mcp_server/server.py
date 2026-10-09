"""Campus Customs MCP server.

Shared toolbox for every agent on the Campus Customs operations team.
All tools read and write the working copy data/campus_customs_new.db and only
return what is in the database. If a row is missing, the tool says so
instead of guessing.

Money rules enforced here (not just in prompts):
- Agents can only *request* payments and purchase orders. Requests sit in
  approval_requests as "pending" until a human decides.
- decide_approval_request is the only tool that moves cash, and it is for the
  human approval step only (agents are never given it).
- A payment that would make an account negative is refused.
- Customer messages are saved as drafts on the board; nothing is ever sent.
"""

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

DB_PATH = Path(
    os.environ.get(
        "CAMPUS_CUSTOMS_DB",
        Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db",
    )
)

mcp = FastMCP("campus-customs")

TICKET_STATUSES = ("open", "in_progress", "waiting_approval", "blocked", "resolved")


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Board tables the agents write to. Created on the working copy if missing,
    so a freshly reset copy of the original database works without manual setup."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL,              -- invoice | rent | purchase_order
            ref_id INTEGER,                  -- invoices.id, leases.id, or NULL for a PO
            payee TEXT NOT NULL,
            amount REAL NOT NULL,
            account TEXT NOT NULL,
            ticket_id INTEGER,
            requested_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            details TEXT,                    -- PO line: vendor, sku, size, qty, arrival
            status TEXT NOT NULL,            -- pending | paid | rejected
            created_at TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            decision_note TEXT
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            drafted_by TEXT NOT NULL,
            status TEXT NOT NULL,            -- always 'draft'; nothing is sent
            created_at TEXT NOT NULL
        );
        """
    )


def _today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' comes from desk.date_today, never the real clock."""
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _add_one_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    raise ValueError(iso_day)


def _open_invoices_for_vendor(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, amount, due_date, description FROM invoices "
        "WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Desk and tickets
# ---------------------------------------------------------------------------


@mcp.tool
def get_desk_date() -> dict:
    """Return the shop's 'today' (desk.date_today) and desk notes.

    Always use this date for overdue / due-soon math, never the real clock.
    """
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    return {"date_today": row["date_today"], "notes": row["notes"]}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket on the board that is not resolved yet."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY id"
        ).fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket on the board (open and resolved) with its status."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        today = _today(conn)
    return {"date_today": today, "count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with everything it links to.

    Includes the ticket row plus any linked inventory (sku/size), lease,
    invoice, drafts, and approval requests already raised for it.
    """
    with _connect() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"found": False, "error": f"No ticket with id {ticket_id}."}
        ticket = dict(t)
        linked: dict = {}
        if ticket["sku"]:
            q = "SELECT * FROM inventory WHERE sku = ?"
            args: tuple = (ticket["sku"],)
            if ticket["size"]:
                q += " AND size = ?"
                args += (ticket["size"],)
            linked["inventory"] = [dict(r) for r in conn.execute(q, args).fetchall()]
        if ticket["lease_id"] is not None:
            r = conn.execute("SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
            linked["lease"] = dict(r) if r else None
        if ticket["invoice_id"] is not None:
            r = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ticket["invoice_id"],),
            ).fetchone()
            linked["invoice"] = dict(r) if r else None
        linked["drafts"] = [
            dict(r) for r in conn.execute("SELECT * FROM drafts WHERE ticket_id = ?", (ticket_id,))
        ]
        linked["approval_requests"] = [
            dict(r)
            for r in conn.execute("SELECT * FROM approval_requests WHERE ticket_id = ?", (ticket_id,))
        ]
        today = _today(conn)
    return {"found": True, "date_today": today, "ticket": ticket, "linked": linked}


@mcp.tool
def update_ticket(
    ticket_id: int,
    status: Literal["open", "in_progress", "waiting_approval", "blocked", "resolved"],
    note: str,
    updated_by: str,
) -> dict:
    """Set a ticket's status and append a short note explaining the call.

    The original ticket notes are kept; the new note is appended with the
    shop date and who wrote it.
    """
    with _connect() as conn:
        t = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "error": f"No ticket with id {ticket_id}."}
        today = _today(conn)
        notes = (t["notes"] or "").rstrip()
        notes = f"{notes}\n[{today} {updated_by}] {note}".strip()
        conn.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id)
        )
    return {"ok": True, "ticket_id": ticket_id, "status": status, "notes": notes}


# ---------------------------------------------------------------------------
# Inventory, pricing, vendors
# ---------------------------------------------------------------------------


@mcp.tool
def check_stock(sku: str, size: str | None = None) -> dict:
    """Look up how many units of a SKU are on hand, per size.

    Pass a size (e.g. "S", "M", "OS") to check one size, or leave it out to
    see every size of that SKU. Returns qty and shelf location from the
    inventory table.
    """
    with _connect() as conn:
        if size:
            rows = conn.execute(
                "SELECT sku, name, size, qty, location FROM inventory "
                "WHERE sku = ? AND size = ?",
                (sku, size),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
                (sku,),
            ).fetchall()

    if not rows:
        target = f"{sku} size {size}" if size else sku
        return {"found": False, "error": f"No inventory row for {target}."}
    return {"found": True, "items": [dict(r) for r in rows]}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Get a SKU's unit cost and list price, plus the margin per unit.

    Use this before agreeing to any discount so the price never drops below
    what the shop paid for the item.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        ).fetchone()

    if row is None:
        return {"found": False, "error": f"No pricing row for {sku}."}
    pricing = dict(row)
    margin = pricing["list_price"] - pricing["unit_cost"]
    return {
        "found": True,
        "pricing": pricing,
        "margin_per_unit": round(margin, 2),
        "margin_pct_of_list": round(margin / pricing["list_price"] * 100, 1),
    }


@mcp.tool
def quote_discount(sku: str, qty: int, discount_pct: float) -> dict:
    """Price a bulk order at a given % off list and show the margin that is left.

    Does the math from the pricing table so agents never do it in their head.
    Flags any quote that would sell at or below unit cost.
    """
    if qty <= 0 or not (0 <= discount_pct < 100):
        return {"ok": False, "error": "qty must be > 0 and discount_pct between 0 and 100."}
    with _connect() as conn:
        row = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if row is None:
        return {"ok": False, "error": f"No pricing row for {sku}."}
    unit_cost, list_price = row["unit_cost"], row["list_price"]
    unit_price = round(list_price * (1 - discount_pct / 100), 2)
    margin_per_unit = round(unit_price - unit_cost, 2)
    return {
        "ok": True,
        "sku": sku,
        "qty": qty,
        "discount_pct": discount_pct,
        "list_price": list_price,
        "unit_cost": unit_cost,
        "discounted_unit_price": unit_price,
        "order_total": round(unit_price * qty, 2),
        "total_cost": round(unit_cost * qty, 2),
        "margin_per_unit": margin_per_unit,
        "total_margin": round(margin_per_unit * qty, 2),
        "margin_pct_of_price": round(margin_per_unit / unit_price * 100, 1) if unit_price else None,
        "below_or_at_cost": margin_per_unit <= 0,
    }


@mcp.tool
def list_vendors() -> dict:
    """List vendors with specialty, lead time, and whether they can ship now.

    A vendor with any open invoice will NOT ship new product, so can_ship is
    False until those invoices are paid. Expected arrival = date_today + lead_days.
    """
    with _connect() as conn:
        today = _today(conn)
        vendors = []
        for v in conn.execute("SELECT * FROM vendors ORDER BY id").fetchall():
            v = dict(v)
            open_inv = _open_invoices_for_vendor(conn, v["id"])
            v["open_invoices"] = open_inv
            v["can_ship"] = not open_inv
            v["arrival_if_ordered_today"] = date.fromordinal(
                date.fromisoformat(today).toordinal() + v["lead_days"]
            ).isoformat()
            vendors.append(v)
    return {"date_today": today, "vendors": vendors}


# ---------------------------------------------------------------------------
# Money: invoices, leases, cash, approvals
# ---------------------------------------------------------------------------


@mcp.tool
def list_invoices(status: Literal["open", "paid", "all"] = "open") -> dict:
    """List vendor invoices with vendor name and overdue status vs date_today."""
    with _connect() as conn:
        today = _today(conn)
        q = (
            "SELECT i.*, v.name AS vendor_name FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id"
        )
        args: tuple = ()
        if status != "all":
            q += " WHERE i.status = ?"
            args = (status,)
        rows = [dict(r) for r in conn.execute(q + " ORDER BY i.due_date", args).fetchall()]
    for r in rows:
        days = _days_between(r["due_date"], today)
        r["days_overdue"] = max(days, 0)
        r["overdue"] = r["status"] == "open" and days > 0
    return {"date_today": today, "invoices": rows}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Get a lease's rent amount, landlord, and next due date.

    Also reports how many days remain until rent is due, measured from the
    shop's date_today in the desk table (negative means overdue).
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        today = _today(conn)

    if row is None:
        return {"found": False, "error": f"No lease with id {lease_id}."}
    lease = dict(row)
    days_until_due = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days
    return {
        "found": True,
        "lease": lease,
        "date_today": today,
        "days_until_due": days_until_due,
        "overdue": days_until_due < 0,
    }


@mcp.tool
def get_cash_balance() -> dict:
    """Cash on hand per account, plus what is already committed to pending
    approval requests, so agents can see what would be left if all are approved.
    Cash only goes out in this shop; no revenue is modeled."""
    with _connect() as conn:
        accounts = [dict(r) for r in conn.execute("SELECT * FROM cash_accounts").fetchall()]
        for a in accounts:
            pending = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS s FROM approval_requests "
                "WHERE account = ? AND status = 'pending'",
                (a["name"],),
            ).fetchone()["s"]
            a["pending_requests_total"] = round(pending, 2)
            a["balance_after_pending"] = round(a["balance"] - pending, 2)
    return {"accounts": accounts}


@mcp.tool
def request_payment(
    kind: Literal["invoice", "rent"],
    ref_id: int,
    reason: str,
    requested_by: str,
    ticket_id: int | None = None,
    account: str = "checking",
) -> dict:
    """Prepare a payment for HUMAN approval. Does not move any money.

    kind="invoice" pays invoices.id = ref_id; kind="rent" pays one month of
    leases.id = ref_id. The amount is always taken from the database, never
    from the caller. Refuses duplicates and anything already paid.
    """
    with _connect() as conn:
        if kind == "invoice":
            r = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if r is None:
                return {"ok": False, "error": f"No invoice with id {ref_id}."}
            if r["status"] != "open":
                return {"ok": False, "error": f"Invoice {ref_id} is '{r['status']}', not open."}
            payee, amount = r["vendor_name"], r["amount"]
        else:
            r = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if r is None:
                return {"ok": False, "error": f"No lease with id {ref_id}."}
            payee, amount = r["landlord"], r["monthly_rent"]
            reason = f"{reason} (rent due {r['next_due']})"

        acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            return {"ok": False, "error": f"No cash account named {account}."}

        dup = conn.execute(
            "SELECT id FROM approval_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'",
            (kind, ref_id),
        ).fetchone()
        if dup:
            return {"ok": False, "error": f"Approval request {dup['id']} is already pending for this."}

        pending = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM approval_requests "
            "WHERE account = ? AND status = 'pending'",
            (account,),
        ).fetchone()["s"]
        cur = conn.execute(
            "INSERT INTO approval_requests (kind, ref_id, payee, amount, account, ticket_id, "
            "requested_by, reason, status, created_at) VALUES (?,?,?,?,?,?,?,?, 'pending', ?)",
            (kind, ref_id, payee, amount, account, ticket_id, requested_by, reason, _now()),
        )
    after = round(acct["balance"] - pending - amount, 2)
    return {
        "ok": True,
        "approval_request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "payee": payee,
        "amount": amount,
        "account": account,
        "balance_now": acct["balance"],
        "balance_if_all_pending_approved": after,
        "warning": "Not enough cash to approve every pending request." if after < 0 else None,
        "note": "Waiting for a human to approve. No money has moved.",
    }


@mcp.tool
def create_purchase_order(
    vendor_id: int,
    sku: str,
    size: str,
    qty: int,
    reason: str,
    requested_by: str,
    ticket_id: int | None = None,
    account: str = "checking",
) -> dict:
    """Prepare a restock purchase order for HUMAN approval. Does not move money.

    Cost = pricing.unit_cost x qty. Refuses if the vendor has any open
    invoice (they will not ship), or if the sku/size does not exist.
    Reports the expected arrival date from vendors.lead_days.
    """
    if qty <= 0:
        return {"ok": False, "error": "qty must be > 0."}
    with _connect() as conn:
        v = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if v is None:
            return {"ok": False, "error": f"No vendor with id {vendor_id}."}
        open_inv = _open_invoices_for_vendor(conn, vendor_id)
        if open_inv:
            return {
                "ok": False,
                "error": f"{v['name']} will not ship while invoice(s) "
                f"{[i['id'] for i in open_inv]} are unpaid. Pay those first.",
                "open_invoices": open_inv,
            }
        item = conn.execute(
            "SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if item is None or price is None:
            return {"ok": False, "error": f"No inventory/pricing for {sku} size {size}."}
        today = _today(conn)
        arrival = date.fromordinal(date.fromisoformat(today).toordinal() + v["lead_days"]).isoformat()
        amount = round(price["unit_cost"] * qty, 2)
        details = (
            f"PO to {v['name']}: {qty} x {sku} size {size} @ ${price['unit_cost']:.2f}; "
            f"lead {v['lead_days']} days, expected arrival {arrival}"
        )
        cur = conn.execute(
            "INSERT INTO approval_requests (kind, ref_id, payee, amount, account, ticket_id, "
            "requested_by, reason, details, status, created_at) "
            "VALUES ('purchase_order', NULL, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (v["name"], amount, account, ticket_id, requested_by, reason, details, _now()),
        )
    return {
        "ok": True,
        "approval_request_id": cur.lastrowid,
        "status": "pending",
        "amount": amount,
        "details": details,
        "expected_arrival": arrival,
        "note": "Waiting for a human to approve. No money has moved.",
    }


@mcp.tool
def list_approval_requests(status: Literal["pending", "paid", "rejected", "all"] = "pending") -> dict:
    """List payment / purchase-order requests waiting on (or decided by) a human."""
    with _connect() as conn:
        q = "SELECT * FROM approval_requests"
        args: tuple = ()
        if status != "all":
            q += " WHERE status = ?"
            args = (status,)
        rows = [dict(r) for r in conn.execute(q + " ORDER BY id", args).fetchall()]
    return {"requests": rows}


@mcp.tool
def decide_approval_request(
    request_id: int,
    decision: Literal["approve", "reject"],
    approver: str,
    note: str = "",
) -> dict:
    """HUMAN APPROVAL STEP ONLY — agents are never given this tool.

    approve: pays the request. Refuses if cash would go negative. On success
    writes a payments row, lowers cash_accounts.balance, and updates the source
    table (invoice -> 'paid', lease.next_due -> next month).
    reject: marks the request rejected; no money moves.
    """
    with _connect() as conn:
        req = conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"ok": False, "error": f"No approval request {request_id}."}
        if req["status"] != "pending":
            return {"ok": False, "error": f"Request {request_id} is already '{req['status']}'."}
        today = _today(conn)

        if decision == "reject":
            conn.execute(
                "UPDATE approval_requests SET status='rejected', decided_by=?, decided_at=?, "
                "decision_note=? WHERE id=?",
                (approver, _now(), note, request_id),
            )
            return {"ok": True, "request_id": request_id, "status": "rejected"}

        acct = conn.execute(
            "SELECT * FROM cash_accounts WHERE name = ?", (req["account"],)
        ).fetchone()
        if acct is None:
            return {"ok": False, "error": f"No cash account {req['account']}."}
        if acct["balance"] < req["amount"]:
            return {
                "ok": False,
                "error": f"Refused: {req['account']} has ${acct['balance']:.2f}, "
                f"payment is ${req['amount']:.2f}. Balances cannot go negative.",
            }
        new_balance = round(acct["balance"] - req["amount"], 2)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today, req["account"]),
        )
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?,?,?,?,?,?)",
            (
                req["kind"],
                req["ref_id"] if req["ref_id"] is not None else request_id,
                req["amount"],
                req["account"],
                today,
                approver,
            ),
        )
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
        elif req["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            conn.execute(
                "UPDATE leases SET next_due = ? WHERE id = ?",
                (_add_one_month(lease["next_due"]), req["ref_id"]),
            )
        conn.execute(
            "UPDATE approval_requests SET status='paid', decided_by=?, decided_at=?, "
            "decision_note=? WHERE id=?",
            (approver, _now(), note, request_id),
        )
    return {
        "ok": True,
        "request_id": request_id,
        "status": "paid",
        "payment_id": pay.lastrowid,
        "amount": req["amount"],
        "account": req["account"],
        "new_balance": new_balance,
    }


# ---------------------------------------------------------------------------
# Customer drafts
# ---------------------------------------------------------------------------


@mcp.tool
def draft_customer_message(
    ticket_id: int, recipient: str, subject: str, body: str, drafted_by: str
) -> dict:
    """Save a customer-facing message as a DRAFT on the board. Never sends it."""
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"ok": False, "error": f"No ticket with id {ticket_id}."}
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, subject, body, drafted_by, status, created_at) "
            "VALUES (?,?,?,?,?, 'draft', ?)",
            (ticket_id, recipient, subject, body, drafted_by, _now()),
        )
    return {"ok": True, "draft_id": cur.lastrowid, "status": "draft", "sent": False}


@mcp.tool
def list_drafts(ticket_id: int | None = None) -> dict:
    """List customer message drafts on the board (optionally for one ticket)."""
    with _connect() as conn:
        if ticket_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,)
            ).fetchall()
    return {"drafts": [dict(r) for r in rows]}


if __name__ == "__main__":
    mcp.run(show_banner=False)
