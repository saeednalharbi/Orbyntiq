import json
from typing import Any

from langchain_core.messages import AIMessage

from orbyntiq.agents.contracts import AgentResult, AgentStatus
from orbyntiq.agents.state import AgentState
from orbyntiq.services import LLMService

SYNTHESIZER_SYSTEM_PROMPT = """
You are the final response synthesizer inside Orbyntiq.

Your responsibility is to turn successful agent output into the final
user-facing answer.

Rules:
- Use only information contained in the supplied agent results.
- Never invent tool results, retrieved facts, citations, or external actions.
- Never add a citation unless that citation exists in the supplied sources.
- Preserve exact identifiers, names, status values, numbers, and protocol names.
- Preserve useful citations such as [S1] and [S2] when they actually exist.
- Do not expose internal routing or orchestration metadata.
- Keep the response concise and directly relevant.
""".strip()


def _successful_results(
    state: AgentState,
) -> list[dict[str, Any]]:
    return [
        result
        for result in state["agent_results"]
        if result.get("status") == AgentStatus.SUCCESS
        and str(result.get("content", "")).strip()
    ]


def _failure_update(
    state: AgentState,
    *,
    error: str,
    final_response: str,
) -> dict[str, Any]:
    result = AgentResult(
        agent="synthesizer",
        status=AgentStatus.FAILED,
        error=error,
    )

    return {
        "active_agent": "synthesizer",
        "agent_results": [
            result.model_dump(mode="json"),
        ],
        "errors": [error],
        "final_response": final_response,
        "messages": [
            AIMessage(content=final_response),
        ],
        "hop_count": state["hop_count"] + 1,
    }


def _format_mcp_result(
    result: dict[str, Any],
) -> str:
    content = str(result.get("content", "")).strip()

    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content

    if not isinstance(payload, dict):
        return content

    answer = payload.get("answer")

    if isinstance(answer, str) and answer.strip():
        return answer.strip()

    service = payload.get("service")
    status = payload.get("status")
    protocol = payload.get("protocol")

    if (
        isinstance(service, str)
        and isinstance(status, str)
        and isinstance(protocol, str)
    ):
        return (
            f"{service} status is {status} "
            f"(protocol: {protocol})."
        )

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
    )


class SynthesizerAgent:
    """Produce the final user-facing response from agent results."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def _synthesize_with_llm(
        self,
        state: AgentState,
        results: list[dict[str, Any]],
    ) -> str:
        payload = {
            "user_query": state["user_query"],
            "route": state["route"],
            "agent_results": results,
            "sources": state["sources"],
        }

        prompt = (
            "Create the final answer for the user using only the "
            "execution data below.\n\n"
            f"{json.dumps(payload, indent=2, ensure_ascii=False)}"
        )

        response = await self._llm_service.chat(
            prompt,
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        )

        return response.content.strip()

    async def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        """Finalize the current multi-agent execution."""

        results = _successful_results(state)

        if not results:
            return _failure_update(
                state,
                error=(
                    "No successful agent result is available "
                    "for synthesis."
                ),
                final_response=(
                    "I couldn't complete the request because the "
                    "selected operation did not succeed."
                ),
            )

        if len(results) == 1 and state["route"] in {
            "general",
            "research",
        }:
            final_response = str(
                results[0]["content"]
            ).strip()

            mode = "passthrough"

        elif len(results) == 1 and state["route"] == "mcp":
            final_response = _format_mcp_result(
                results[0]
            )

            mode = "mcp_structured"

        else:
            final_response = await self._synthesize_with_llm(
                state,
                results,
            )

            mode = "llm"

            if not final_response:
                return _failure_update(
                    state,
                    error=(
                        "Synthesizer received an empty "
                        "LLM response."
                    ),
                    final_response=(
                        "I couldn't produce a final response."
                    ),
                )

        result = AgentResult(
            agent="synthesizer",
            status=AgentStatus.SUCCESS,
            content=final_response,
            metadata={
                "mode": mode,
                "route": state["route"],
                "source_result_count": len(results),
            },
            sources=state["sources"],
        )

        return {
            "active_agent": "synthesizer",
            "agent_results": [
                result.model_dump(mode="json"),
            ],
            "final_response": final_response,
            "messages": [
                AIMessage(content=final_response),
            ],
            "hop_count": state["hop_count"] + 1,
        }
