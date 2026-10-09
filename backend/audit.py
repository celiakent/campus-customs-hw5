"""Append-only audit trail at output/audit_trail.json.

The file is a JSON array. Every agent-loop step is appended; the file is never
wiped between runs. A lock keeps concurrent agents from clobbering each other.
"""

import json
import threading
from datetime import datetime, timezone
from typing import Any

from config import AUDIT_TEXT_LIMIT, AUDIT_TRAIL, MODEL_NAME
from models import AuditEvent, TeamDeps

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > AUDIT_TEXT_LIMIT:
        return value[:AUDIT_TEXT_LIMIT] + f"... [+{len(value) - AUDIT_TEXT_LIMIT} chars]"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value]
    return value


def record(deps: TeamDeps, step: int, event: str, data: dict[str, Any] | None = None) -> None:
    entry = AuditEvent(
        ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        run_id=deps.run_id,
        ticket_id=deps.ticket_id,
        agent=deps.agent,
        depth=deps.depth,
        chain=list(deps.chain),
        step=step,
        event=event,  # type: ignore[arg-type]
        model=MODEL_NAME,
        data=_clip(data or {}),
    )
    with _lock:
        AUDIT_TRAIL.parent.mkdir(parents=True, exist_ok=True)
        try:
            trail = json.loads(AUDIT_TRAIL.read_text()) if AUDIT_TRAIL.exists() else []
            if not isinstance(trail, list):
                trail = [trail]
        except json.JSONDecodeError:
            # never destroy history: keep the unreadable file aside and start fresh
            AUDIT_TRAIL.rename(AUDIT_TRAIL.with_suffix(f".corrupt-{int(datetime.now().timestamp())}.json"))
            trail = []
        trail.append(entry.model_dump(mode="json"))
        tmp = AUDIT_TRAIL.with_suffix(".tmp")
        tmp.write_text(json.dumps(trail, indent=2, default=str))
        tmp.replace(AUDIT_TRAIL)


def read_trail(run_id: str | None = None, ticket_id: int | None = None) -> list[dict]:
    if not AUDIT_TRAIL.exists():
        return []
    trail = json.loads(AUDIT_TRAIL.read_text())
    return [
        e
        for e in trail
        if (run_id is None or e["run_id"] == run_id)
        and (ticket_id is None or e["ticket_id"] == ticket_id)
    ]
