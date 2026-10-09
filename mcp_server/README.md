# Campus Customs MCP Server

A [FastMCP](https://gofastmcp.com) server that is the shared toolbox for the Campus Customs multi-agent team (Boss, Inventory, Accounting, Facilities, Customer Service). Agents call these tools to get real facts from the shop database instead of guessing. Every answer comes straight from the database, and a missing row returns `found: false` (or `ok: false`) with an error.

## Database

- Uses **`data/campus_customs_new.db`**, the working copy.
- The original `data/campus_customs.db` is never touched. Reset with `POST /api/reset` or `python reset_db.py` from `backend/`.
- Set `CAMPUS_CUSTOMS_DB` to point at a different file.
- On startup the server creates two board tables on the working copy if they're missing: `approval_requests` (payments and purchase orders waiting for a human) and `drafts` (customer messages, never sent).

## Tools

| Tool | Reads / writes | What it does |
|---|---|---|
| `get_desk_date` | desk | The shop's "today" (`desk.date_today`) |
| `list_open_tickets` | tickets | Every ticket that isn't resolved |
| `list_tickets` | tickets | Every ticket (open and resolved) with its status |
| `get_ticket` | tickets + linked inventory, lease, invoice, drafts, approvals | One ticket with everything it links to |
| `update_ticket` | tickets | Sets status and appends a dated note |
| `check_stock` | inventory | Qty and location per SKU and size |
| `get_pricing` | pricing | Unit cost, list price, margin |
| `quote_discount` | pricing | Bulk order math at a given % off, flags below-cost quotes |
| `list_vendors` | vendors, invoices | Specialty, lead days, `can_ship` (false if an invoice is open), arrival date |
| `list_invoices` | invoices, vendors | Invoices with days overdue |
| `get_lease` | leases | Rent, landlord, next due date, days until due |
| `get_cash_balance` | cash_accounts, approval_requests | Balance and balance after pending requests |
| `request_payment` | invoices or leases → approval_requests | Creates a **pending** invoice or rent payment (amount taken from the DB) |
| `create_purchase_order` | vendors, pricing, inventory → approval_requests | Creates a **pending** restock PO, refused if the vendor has an open invoice |
| `list_approval_requests` | approval_requests | Pending, paid, or rejected requests |
| `draft_customer_message` | drafts | Saves a customer message as a draft (never sent) |
| `list_drafts` | drafts | Drafts on the board, optionally for one ticket |
| `decide_approval_request` | approval_requests, cash_accounts, payments, invoices, leases | **Human approval step only (`POST /api/approvals/{id}/approve`), never given to agents.** Pays (refuses if cash would go negative) or rejects |

## Run

The backend starts this server over stdio automatically. To use it from Claude Code, see `.mcp.json` at the project root. To run it by hand:

```bash
python mcp_server/server.py
```
