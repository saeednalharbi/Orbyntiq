from typing import Any

from orbyntiq.agents.contracts import AgentResult, AgentStatus
from orbyntiq.agents.state import AgentState
from orbyntiq.services import LLMService

GENERAL_AGENT_SYSTEM_PROMPT = """
You are the general-purpose reasoning agent inside Orbyntiq.

Answer requests that do not require document retrieval or MCP tool execution.

Rules:
- Answer the user's request directly.
- Be accurate and concise.
- Do not claim to have searched documents unless retrieval actually occurred.
- Do not claim to have executed tools or external actions.
- If information is uncertain, say so clearly.
""".strip()


class GeneralAgent:
    """Handle requests that require only the configured LLM."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        """Generate a direct LLM answer and return a graph update."""

        response = await self._llm_service.chat(
            state["user_query"],
            system_prompt=GENERAL_AGENT_SYSTEM_PROMPT,
        )

        content = response.content.strip()

        if not content:
            error_message = (
                "General agent received an empty LLM response."
            )

            result = AgentResult(
                agent="general",
                status=AgentStatus.FAILED,
                error=error_message,
                metadata={
                    "model": response.model,
                },
            )

            return {
                "active_agent": "general",
                "agent_results": [
                    result.model_dump(mode="json"),
                ],
                "errors": [error_message],
                "hop_count": state["hop_count"] + 1,
            }

        result = AgentResult(
            agent="general",
            status=AgentStatus.SUCCESS,
            content=content,
            metadata={
                "model": response.model,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
            },
        )

        return {
            "active_agent": "general",
            "agent_results": [
                result.model_dump(mode="json"),
            ],
            "hop_count": state["hop_count"] + 1,
        }
