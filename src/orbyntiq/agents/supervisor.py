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


class SupervisorAgent:
    """Route Orbyntiq requests to the appropriate specialized agent."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def decide(self, state: AgentState) -> RoutingDecision:
        """Produce a validated routing decision for the current request."""

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
