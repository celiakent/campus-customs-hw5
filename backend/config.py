"""Paths, limits, and the one model every agent uses."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

load_dotenv(ROOT_DIR / ".env", override=True)
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

DATA_DIR = ROOT_DIR / "data"
ORIGINAL_DB = DATA_DIR / "campus_customs.db"
WORKING_DB = DATA_DIR / "campus_customs_new.db"
MCP_SERVER_SCRIPT = ROOT_DIR / "mcp_server" / "server.py"
PROMPTS_DIR = BACKEND_DIR / "prompts"
AUDIT_TRAIL = ROOT_DIR / "output" / "audit_trail.json"

# The assignment allows exactly one model for every agent. It is fixed here on
# purpose (no env override) so nothing else can sneak into a run.
MODEL_NAME = "gpt-6-luna"

# --- Token / cost guardrails -------------------------------------------------
# Shared across the whole ticket run (Boss + every delegated agent).
TEAM_USAGE_LIMITS = UsageLimits(
    request_limit=40,          # model calls per ticket, all agents combined
    tool_calls_limit=60,       # MCP + delegate calls per ticket
    total_tokens_limit=250_000,
)
MAX_DELEGATION_DEPTH = 3       # boss -> a -> b -> c, no deeper
MAX_DELEGATIONS_PER_TICKET = 8
# gpt-6-luna's hidden reasoning counts toward max_tokens, so the cap has to
# leave room for thinking *and* the answer (4000 was too tight for Boss's final
# decision). Low reasoning effort keeps each call short and cheap.
MODEL_SETTINGS = OpenAIResponsesModelSettings(
    max_tokens=12_000,
    openai_reasoning_effort="low",
)
AUDIT_TEXT_LIMIT = 2000        # truncate long strings in the audit trail


class MissingAPIKey(RuntimeError):
    pass


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey's OpenAI-compatible gateway.

    Uses the Responses API (/v1/responses): gpt-6-luna does not allow function
    tools together with reasoning on /v1/chat/completions.
    """
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise MissingAPIKey("PORTKEY_API_KEY is not set. Copy .env.example to .env and add it.")
    client = AsyncOpenAI(
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        api_key=api_key,
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
