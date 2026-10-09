"""The Campus Customs agent team: Boss, Inventory, Accounting, Facilities,
Customer Service.

- Every agent runs on gpt-6-luna through Portkey (see config.py).
- Shop facts come only from the MCP server (mcp_server/server.py) over the
  working database. Each agent sees just the MCP tools its job needs.
- Full connectivity: every agent has a `delegate` tool that can hand a task
  to any other agent. Team-wide limits (depth, count, tokens) stop runaway
  chains.
- Each agent loop is driven with Agent.iter so every step is appended to
  output/audit_trail.json as it happens.
"""

import json
import sys
import uuid
from dataclasses import replace
from functools import lru_cache

from fastmcp.client.transports import PythonStdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import RunUsage

import audit
from config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MCP_SERVER_SCRIPT,
    MODEL_SETTINGS,
    PROMPTS_DIR,
    TEAM_USAGE_LIMITS,
    WORKING_DB,
    build_model,
)
from models import AGENT_NAMES, AgentName, BossDecision, SpecialistReport, TeamDeps

# ---------------------------------------------------------------------------
# MCP: one connection to the shop server, filtered per agent
# ---------------------------------------------------------------------------

shop_mcp = MCPToolset(
    PythonStdioTransport(
        script_path=MCP_SERVER_SCRIPT,
        python_cmd=sys.executable,
        env={"CAMPUS_CUSTOMS_DB": str(WORKING_DB)},
    ),
    id="campus_customs_mcp",
)

# Tools that move money. No agent gets these; only the human approval step does.
HUMAN_ONLY_TOOLS = {"decide_approval_request"}

TOOL_ACCESS: dict[AgentName, set[str]] = {
    "boss": {
        "get_desk_date", "list_open_tickets", "get_ticket", "update_ticket",
        "list_approval_requests", "get_cash_balance",
    },
    "inventory": {
        "get_desk_date", "get_ticket", "check_stock", "list_vendors",
        "list_invoices", "get_pricing",
    },
    "accounting": {
        "get_desk_date", "get_ticket", "get_cash_balance", "list_invoices",
        "list_vendors", "get_pricing", "quote_discount", "get_lease",
        "request_payment", "create_purchase_order", "list_approval_requests",
    },
    "facilities": {"get_desk_date", "get_ticket", "get_lease", "list_approval_requests"},
    "customer_service": {
        "get_desk_date", "get_ticket", "check_stock", "get_pricing",
        "quote_discount", "list_vendors", "draft_customer_message",
    },
}
assert not any(tools & HUMAN_ONLY_TOOLS for tools in TOOL_ACCESS.values())

TEAM_ROSTER = {
    "boss": "Boss: reads tickets, decides who works on them, makes the final call, sets ticket status.",
    "inventory": "Inventory: stock by SKU and size, shortfalls, which vendor can restock and when.",
    "accounting": "Accounting: cash, invoices, margins, discount math; prepares payments and purchase orders for human approval.",
    "facilities": "Facilities: the shop space, leases, rent amounts and due dates.",
    "customer_service": "Customer Service: drafts messages to customers and requesters (drafts only, never sent).",
}


def _mcp_for(name: AgentName):
    allowed = TOOL_ACCESS[name]
    return shop_mcp.filtered(lambda ctx, tool_def: tool_def.name in allowed)


# ---------------------------------------------------------------------------
# Delegation: any agent -> any other agent
# ---------------------------------------------------------------------------

delegation_tools: FunctionToolset[TeamDeps] = FunctionToolset()


@delegation_tools.tool
async def delegate(ctx: RunContext[TeamDeps], to_agent: AgentName, task: str) -> str:
    """Hand a focused task to a teammate and get their report back.

    Teammates: boss, inventory, accounting, facilities, customer_service.
    Write `task` so it stands on its own: include the ticket id and the exact
    facts or numbers you already have, and say what you need back.
    You cannot delegate to yourself or to anyone already in the current chain.
    """
    deps = ctx.deps
    refusal = None
    if to_agent == deps.agent:
        refusal = "You cannot delegate to yourself."
    elif to_agent in deps.chain:
        refusal = f"{to_agent} is already working on this chain ({' -> '.join(deps.chain)}); answer with what you have."
    elif deps.depth + 1 > MAX_DELEGATION_DEPTH:
        refusal = f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached; finish with what you have."
    elif deps.counters["delegations"] >= MAX_DELEGATIONS_PER_TICKET:
        refusal = f"Team delegation limit ({MAX_DELEGATIONS_PER_TICKET}) reached for this ticket."
    if refusal:
        audit.record(deps, 0, "delegation_refused", {"to_agent": to_agent, "task": task, "reason": refusal})
        return f"DELEGATION REFUSED: {refusal}"

    deps.counters["delegations"] += 1
    child = replace(
        deps,
        agent=to_agent,
        depth=deps.depth + 1,
        chain=[*deps.chain, to_agent],
    )
    audit.record(deps, 0, "delegation_start", {"to_agent": to_agent, "task": task})
    try:
        output = await run_agent(to_agent, task, child, usage=ctx.usage)
    except UsageLimitExceeded:
        raise
    except Exception as exc:  # teammate crashed: tell the caller, don't kill the run
        audit.record(deps, 0, "delegation_end", {"to_agent": to_agent, "error": repr(exc)})
        return f"{to_agent} failed: {exc!r}"
    report = output.model_dump()
    audit.record(deps, 0, "delegation_end", {"to_agent": to_agent, "report": report})
    return json.dumps(report)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


def _load_prompt(name: AgentName) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


@lru_cache(maxsize=1)
def get_team() -> dict[AgentName, Agent]:
    model = build_model()
    team: dict[AgentName, Agent] = {}
    for name in AGENT_NAMES:
        agent = Agent(
            model,
            name=name,
            deps_type=TeamDeps,
            output_type=BossDecision if name == "boss" else SpecialistReport,
            instructions=_load_prompt(name),
            toolsets=[_mcp_for(name), delegation_tools],
            model_settings=MODEL_SETTINGS,
            retries=2,
        )

        @agent.instructions
        def _context(ctx: RunContext[TeamDeps]) -> str:
            d = ctx.deps
            teammates = "\n".join(f"- {v}" for k, v in TEAM_ROSTER.items() if k != d.agent)
            return (
                f"## Run context\n"
                f"Ticket: {d.ticket_id}. Delegation chain so far: {' -> '.join(d.chain)}.\n"
                f"Delegation depth {d.depth}/{MAX_DELEGATION_DEPTH}; "
                f"team delegations used {d.counters['delegations']}/{MAX_DELEGATIONS_PER_TICKET}.\n"
                f"Teammates you can `delegate` to:\n{teammates}"
            )

        team[name] = agent
    return team


# ---------------------------------------------------------------------------
# Agent loop with audit logging
# ---------------------------------------------------------------------------


def _request_data(parts) -> tuple[str, dict]:
    tool_results, prompts, retries = [], [], []
    for p in parts:
        if isinstance(p, ToolReturnPart):
            tool_results.append({"tool": p.tool_name, "call_id": p.tool_call_id, "result": p.model_response_str()})
        elif isinstance(p, RetryPromptPart):
            retries.append({"tool": p.tool_name, "message": p.model_response()})
        elif isinstance(p, UserPromptPart):
            prompts.append(p.content if isinstance(p.content, str) else str(p.content))
    if tool_results or retries:
        return "tool_results", {"tool_results": tool_results, "retries": retries}
    return "model_request", {"user_prompt": "\n".join(prompts)}


def _response_data(response) -> dict:
    calls, text, thinking = [], [], []
    for p in response.parts:
        if isinstance(p, ToolCallPart):
            calls.append({"tool": p.tool_name, "call_id": p.tool_call_id, "args": p.args_as_dict()})
        elif isinstance(p, TextPart):
            text.append(p.content)
        elif isinstance(p, ThinkingPart) and p.content:
            thinking.append(p.content)
    u = response.usage
    return {
        "model_name": response.model_name,
        "tool_calls": calls,
        "text": "\n".join(text),
        "thinking": "\n".join(thinking) or None,
        "usage": {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens},
    }


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage | None = None):
    """Run one agent's loop step by step, appending each step to the audit trail."""
    agent = get_team()[name]
    step = 0
    audit.record(deps, step, "run_start", {"prompt": prompt})
    try:
        async with agent.iter(
            prompt,
            deps=deps,
            usage=usage,
            usage_limits=TEAM_USAGE_LIMITS,
        ) as run:
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    continue
                step += 1
                if Agent.is_model_request_node(node):
                    event, data = _request_data(node.request.parts)
                    audit.record(deps, step, event, data)
                elif Agent.is_call_tools_node(node):
                    audit.record(deps, step, "model_response", _response_data(node.model_response))
                elif Agent.is_end_node(node):
                    u = run.usage
                    audit.record(
                        deps,
                        step,
                        "final_output",
                        {
                            "output": node.data.output.model_dump(),
                            "team_usage_so_far": {
                                "requests": u.requests,
                                "tool_calls": u.tool_calls,
                                "input_tokens": u.input_tokens,
                                "output_tokens": u.output_tokens,
                            },
                        },
                    )
        return run.result.output
    except Exception as exc:
        audit.record(deps, step, "error", {"error": repr(exc)})
        raise


async def run_ticket(ticket_id: int, run_id: str | None = None) -> dict:
    """Boss takes a ticket and works it with the team. Returns Boss's decision."""
    deps = TeamDeps(
        run_id=run_id or new_run_id(), ticket_id=ticket_id, agent="boss", chain=["boss"]
    )
    prompt = (
        f"Work ticket {ticket_id}. Read it, pull in the teammates it needs, make the final call, "
        f"and set the ticket status with update_ticket before you answer."
    )
    async with shop_mcp:
        decision = await run_agent("boss", prompt, deps)
    return {"run_id": deps.run_id, "ticket_id": ticket_id, "decision": decision.model_dump()}


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def call_shop_tool(name: str, args: dict | None = None) -> dict:
    """Call an MCP tool directly (no agent). Used by the API routes and the
    human approval step, so shop data still only comes through the MCP server."""
    async with shop_mcp:
        result = await shop_mcp.client.call_tool(name, args or {}, raise_on_error=False)
    if result.is_error:
        text = " ".join(getattr(c, "text", "") for c in result.content)
        raise RuntimeError(f"MCP tool {name} failed: {text}")
    return result.data if result.data is not None else result.structured_content
