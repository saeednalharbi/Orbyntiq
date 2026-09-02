from typing import Any

from orbyntiq.agents.contracts import RoutingDecision
from orbyntiq.agents.state import AgentState
from orbyntiq.services import LLMService

SUPERVISOR_SYSTEM_PROMPT = """
You are the supervisor agent inside Orbyntiq.

Your only responsibility is to decide which specialized agent should handle
the user's request.

Available routes:

research:
Use when the request requires information from documents, uploaded files,
indexed knowledge, the RAG pipeline, embeddings, or the Qdrant knowledge base.

mcp:
Use when the request requires executing or using an available MCP tool,
service, capability, or system action.

general:
Use when the request can be answered directly by the language model without
document retrieval or tool execution.

Rules:
- Choose exactly one route.
- Do not answer the user's question.
- Do not execute tools.
- Do not retrieve documents.
- Prefer general when no specialized capability is required.
- Provide a short reason explaining the routing decision.
""".strip()


_RESEARCH_ROUTE_PHRASES = (
    "my knowledge",
    "knowledge base",
    "indexed knowledge",
    "search my knowledge",
    "search the knowledge",
    "using my knowledge",
    "from my knowledge",
    "uploaded document",
    "uploaded documents",
    "uploaded file",
    "uploaded files",
    "my document",
    "my documents",
    "my file",
    "my files",
    "from the documents",
    "in the documents",
)

_MCP_ROUTE_PHRASES = (
    "connected tool",
    "connected tools",
    "mcp tool",
    "mcp tools",
    "use the tool",
    "use a tool",
    "run the tool",
    "execute the tool",
)


def _fast_routing_decision(
    query: str,
) -> RoutingDecision | None:
    """Route explicit specialist intents without an LLM call."""

    normalized = " ".join(query.casefold().split())

    if any(phrase in normalized for phrase in _RESEARCH_ROUTE_PHRASES):
        return RoutingDecision(
            route="research",
            reason=("The request explicitly targets the user's indexed knowledge."),
        )

    if any(phrase in normalized for phrase in _MCP_ROUTE_PHRASES):
        return RoutingDecision(
            route="mcp",
            reason=("The request explicitly requires a connected tool."),
        )

    return None


class SupervisorAgent:
    """Route Orbyntiq requests to the appropriate specialized agent."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def decide(
        self,
        state: AgentState,
    ) -> RoutingDecision:
        """Produce a validated routing decision for the current request."""

        fast_decision = _fast_routing_decision(state["user_query"])

        if fast_decision is not None:
            return fast_decision

        return await self._llm_service.chat_structured(
            state["user_query"],
            RoutingDecision,
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        )

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        """Execute the supervisor node and return a partial graph update."""

        decision = await self.decide(state)

        return {
            "route": decision.route,
            "route_reason": decision.reason,
            "active_agent": "supervisor",
            "hop_count": state["hop_count"] + 1,
        }
