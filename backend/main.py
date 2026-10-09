"""Campus Customs operations API for the React dashboard.

Start from the backend/ folder:

    uvicorn main:app --reload --port 8000

Shop data is read and written only through the MCP server (via
agents.call_shop_tool). The audit trail is read from output/audit_trail.json.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import audit
from agents import call_shop_tool, new_run_id, run_ticket, shop_mcp
from config import MODEL_NAME, WORKING_DB
from reset_db import reset

# In-memory record of agent runs started from the dashboard.
RUNS: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep one MCP server connection open for the whole app; routes and agent
    # runs share it.
    async with shop_mcp:
        yield


app = FastAPI(title="Campus Customs Operations API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _tool(name: str, args: dict | None = None) -> dict:
    try:
        return await call_shop_tool(name, args)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


def _running_ticket_ids() -> set[int]:
    return {r["ticket_id"] for r in RUNS.values() if r["status"] == "running"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    desk = await _tool("get_desk_date")
    return {"ok": True, "model": MODEL_NAME, "db": WORKING_DB.name, "date_today": desk["date_today"]}


# ---------------------------------------------------------------------------
# Tickets and agent runs
# ---------------------------------------------------------------------------


@app.get("/api/tickets")
async def list_tickets():
    """The tickets on the board and whether each is open or resolved."""
    data = await _tool("list_tickets")
    running = _running_ticket_ids()
    tickets = [
        {
            **t,
            "is_resolved": t["status"] == "resolved",
            "agents_running": t["id"] in running,
        }
        for t in data["tickets"]
    ]
    return {"date_today": data["date_today"], "tickets": tickets}


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    data = await _tool("get_ticket", {"ticket_id": ticket_id})
    if not data.get("found"):
        raise HTTPException(status_code=404, detail=data.get("error"))
    return data


async def _do_run(run_id: str, ticket_id: int) -> None:
    try:
        result = await run_ticket(ticket_id, run_id=run_id)
        decision = result["decision"]
        # The team is finished with the ticket once the run ends, so the board
        # marks it resolved. Boss's own status (e.g. waiting_approval) is kept in
        # the run record and the ticket note; pending approvals stay on the
        # ledger until a human decides them.
        pending = decision.get("approvals_needed") or []
        note = f"Agent run {run_id} finished. Boss's call: {decision['status']}."
        if pending:
            note += f" Waiting on human approval: {'; '.join(pending)}."
        await call_shop_tool(
            "update_ticket",
            {"ticket_id": ticket_id, "status": "resolved", "note": note, "updated_by": "desk"},
        )
        RUNS[run_id].update(status="done", decision=decision, boss_status=decision["status"])
    except Exception as exc:
        RUNS[run_id].update(status="error", error=repr(exc))
    RUNS[run_id]["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_agents_on_ticket(ticket_id: int):
    """Start the agent team on a ticket. Returns a run_id right away; poll
    /api/runs/{run_id} and /api/events to watch it."""
    found = await _tool("get_ticket", {"ticket_id": ticket_id})
    if not found.get("found"):
        raise HTTPException(status_code=404, detail=found.get("error"))
    if ticket_id in _running_ticket_ids():
        raise HTTPException(status_code=409, detail=f"Agents are already working ticket {ticket_id}.")
    run_id = new_run_id()
    RUNS[run_id] = {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finished_at": None,
        "decision": None,
        "boss_status": None,
        "error": None,
    }
    asyncio.create_task(_do_run(run_id, ticket_id))
    return RUNS[run_id]


@app.get("/api/runs")
async def list_runs():
    return {"runs": list(RUNS.values())}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail=f"No run {run_id} in this server session.")
    return RUNS[run_id]


# ---------------------------------------------------------------------------
# Agent events (from the audit trail)
# ---------------------------------------------------------------------------


def _event_view(e: dict) -> dict:
    """Flatten one audit entry into what the board shows: who, what they said,
    which tools they called, and what came back."""
    d = e.get("data", {})
    said = None
    tools_called: list[dict] = []
    tool_results: list[dict] = []
    if e["event"] == "model_response":
        said = d.get("text") or None
        tools_called = [
            {"tool": c["tool"], "args": c.get("args")}
            for c in d.get("tool_calls", [])
            if c["tool"] != "final_result"
        ]
    elif e["event"] == "tool_results":
        tool_results = d.get("tool_results", [])
    elif e["event"] == "run_start":
        said = d.get("prompt")
    elif e["event"] == "final_output":
        out = d.get("output", {})
        said = out.get("decision") or out.get("summary")
    elif e["event"] in ("delegation_start", "delegation_refused"):
        said = d.get("task")
    elif e["event"] == "error":
        said = d.get("error")
    return {
        "ts": e["ts"],
        "run_id": e["run_id"],
        "ticket_id": e["ticket_id"],
        "agent": e["agent"],
        "depth": e["depth"],
        "chain": e["chain"],
        "event": e["event"],
        "said": said,
        "tools_called": tools_called,
        "tool_results": tool_results,
        "delegated_to": d.get("to_agent"),
        "output": d.get("output") or d.get("report"),
        "reason": d.get("reason"),
    }


@app.get("/api/events")
async def recent_events(
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
    after: str | None = Query(None, description="only events with ts later than this ISO timestamp"),
):
    """Recent agent events, newest last, for the board to poll."""
    events = audit.read_trail(run_id=run_id, ticket_id=ticket_id)
    if after:
        events = [e for e in events if e["ts"] > after]
    events = events[-limit:]
    return {"count": len(events), "events": [_event_view(e) for e in events]}


# ---------------------------------------------------------------------------
# Approvals: the only place money moves
# ---------------------------------------------------------------------------


class Decision(BaseModel):
    approver: str
    note: str = ""


@app.get("/api/approvals")
async def list_approvals(status: Literal["pending", "paid", "rejected", "all"] = "pending"):
    return await _tool("list_approval_requests", {"status": status})


async def _decide(request_id: int, decision: Literal["approve", "reject"], body: Decision):
    if not body.approver.strip():
        raise HTTPException(status_code=400, detail="approver name is required")
    result = await _tool(
        "decide_approval_request",
        {"request_id": request_id, "decision": decision, "approver": body.approver.strip(), "note": body.note},
    )
    if not result.get("ok"):
        # e.g. not enough cash, already decided, unknown id
        raise HTTPException(status_code=409, detail=result.get("error"))
    return result


@app.post("/api/approvals/{request_id}/approve")
async def approve(request_id: int, body: Decision):
    """A human approved: pay it. Refused if cash would go negative. Writes
    payments, lowers cash_accounts, and marks the invoice/lease as paid."""
    return await _decide(request_id, "approve", body)


@app.post("/api/approvals/{request_id}/reject")
async def reject(request_id: int, body: Decision):
    return await _decide(request_id, "reject", body)


# ---------------------------------------------------------------------------
# Cash, drafts, reset
# ---------------------------------------------------------------------------


@app.get("/api/cash")
async def cash():
    """Current checking balance from cash_accounts (plus what's pending)."""
    data = await _tool("get_cash_balance")
    checking = next((a for a in data["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(status_code=404, detail="No checking account in cash_accounts.")
    return checking


@app.get("/api/drafts")
async def drafts(ticket_id: int | None = None):
    return await _tool("list_drafts", {"ticket_id": ticket_id})


@app.post("/api/reset")
async def reset_database():
    """Copy the original database over the working copy for a fresh run.
    The audit trail is kept (append-only)."""
    if _running_ticket_ids():
        raise HTTPException(status_code=409, detail="Wait for running agents to finish before resetting.")
    reset()
    RUNS.clear()
    tickets = await _tool("list_tickets")
    cash_now = await cash()
    return {
        "ok": True,
        "message": f"{WORKING_DB.name} reset from the original database.",
        "tickets": [{"id": t["id"], "status": t["status"]} for t in tickets["tickets"]],
        "checking_balance": cash_now["balance"],
    }
