"""Data types shared by the Campus Customs agent team."""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

AGENT_NAMES: tuple[AgentName, ...] = (
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
)

TicketStatus = Literal["open", "in_progress", "waiting_approval", "blocked", "resolved"]


@dataclass
class TeamDeps:
    """Context passed to every agent run, including delegated runs.

    One TeamDeps is created per ticket run. Delegated agents get a copy with
    depth + 1 and their own name, but share the same counters so team-wide
    limits hold no matter who delegates to whom.
    """

    run_id: str
    ticket_id: int | None
    agent: AgentName = "boss"
    depth: int = 0
    # chain of agents that led to this run, e.g. ["boss", "inventory"]
    chain: list[AgentName] = field(default_factory=list)
    # shared, mutable across the whole ticket run
    counters: dict[str, int] = field(default_factory=lambda: {"delegations": 0})


class SpecialistReport(BaseModel):
    """What Inventory / Accounting / Facilities / Customer Service hand back."""

    summary: str = Field(description="Two or three sentences answering the request.")
    facts: list[str] = Field(
        default_factory=list,
        description="Numbers and facts from tool results, each with its source table.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Anything written to the board, e.g. 'approval request #2 (rent, $2400)' or 'draft #1'.",
    )
    blockers: list[str] = Field(
        default_factory=list, description="What stops this from moving forward right now."
    )
    recommendation: str = Field(description="What this agent suggests the team do next.")


class BossDecision(BaseModel):
    """Boss's final call on a ticket."""

    ticket_id: int
    status: TicketStatus = Field(description="Status the ticket was set to with update_ticket.")
    decision: str = Field(description="The final call in plain words.")
    reasoning: str = Field(description="Why, citing the facts the team found.")
    agents_consulted: list[AgentName] = Field(default_factory=list)
    approvals_needed: list[str] = Field(
        default_factory=list,
        description="Pending approval requests a human must decide, with id and amount.",
    )
    drafts_for_review: list[str] = Field(
        default_factory=list, description="Customer drafts left on the board, with id."
    )
    next_steps: list[str] = Field(default_factory=list)


class AuditEvent(BaseModel):
    """One line in output/audit_trail.json: one step of an agent loop."""

    ts: str
    run_id: str
    ticket_id: int | None
    agent: AgentName
    depth: int
    chain: list[str]
    step: int
    event: Literal[
        "run_start",
        "model_request",
        "model_response",
        "tool_results",
        "delegation_start",
        "delegation_end",
        "delegation_refused",
        "final_output",
        "error",
    ]
    model: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
