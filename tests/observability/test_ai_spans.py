from collections.abc import AsyncIterator, Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server import MCPServer
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode

import orbyntiq.observability.tracing as tracing_module
from orbyntiq.agents.contracts import MCPToolDecision
from orbyntiq.agents.graph import _instrument_agent_node
from orbyntiq.agents.mcp_agent import MCPAgent
from orbyntiq.agents.state import create_initial_state
from orbyntiq.core.config import Settings
from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.models import LLMMessage, LLMResponse
from orbyntiq.observability.agent_metrics import (
    InstrumentedMultiAgentService,
)
from orbyntiq.rag.retrieval import (
    RetrievalError,
    SemanticRetriever,
)
from orbyntiq.rag.service import RAGService
from orbyntiq.services.llm_service import LLMService


@pytest.fixture
def span_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> InMemorySpanExporter:
    provider = TracerProvider()

    exporter = InMemorySpanExporter()

    provider.add_span_processor(
        SimpleSpanProcessor(
            exporter
        )
    )

    monkeypatch.setattr(
        tracing_module,
        "_tracer_provider",
        provider,
    )

    return exporter


class TraceProvider(LLMProvider):
    model = "trace-model"

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        assert messages

        return LLMResponse(
            content="safe response",
            model=self.model,
            prompt_tokens=11,
            completion_tokens=4,
        )

    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
    ) -> LLMResponse:
        del schema

        assert messages

        return LLMResponse(
            content='{"tool_name":"add_numbers","arguments":{"a":2,"b":3},"reason":"math"}',
            model=self.model,
            prompt_tokens=9,
            completion_tokens=5,
        )

    async def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        assert messages

        yield "first"
        yield "second"


@pytest.mark.anyio
async def test_llm_generate_creates_safe_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    service = LLMService(
        TraceProvider(),
        metrics_enabled=False,
    )

    secret = "PRIVATE_USER_PROMPT_123"

    await service.generate(
        (
            LLMMessage(
                role="user",
                content=secret,
            ),
        )
    )

    spans = span_exporter.get_finished_spans()

    span = next(
        item
        for item in spans
        if item.name == "llm.generate"
    )

    assert (
        span.attributes[
            "gen_ai.request.model"
        ]
        == "trace-model"
    )

    assert (
        span.attributes[
            "gen_ai.usage.input_tokens"
        ]
        == 11
    )

    assert (
        span.attributes[
            "gen_ai.usage.output_tokens"
        ]
        == 4
    )

    assert secret not in str(
        dict(
            span.attributes
        )
    )


@pytest.mark.anyio
async def test_llm_stream_records_chunk_count(
    span_exporter: InMemorySpanExporter,
) -> None:
    service = LLMService(
        TraceProvider(),
        metrics_enabled=False,
    )

    chunks = [
        chunk
        async for chunk in service.generate_stream(
            (
                LLMMessage(
                    role="user",
                    content="stream safely",
                ),
            )
        )
    ]

    assert chunks == [
        "first",
        "second",
    ]

    span = next(
        item
        for item in span_exporter.get_finished_spans()
        if item.name == "llm.stream"
    )

    assert (
        span.attributes[
            "orbyntiq.stream.chunk_count"
        ]
        == 2
    )

    assert (
        span.attributes[
            "orbyntiq.operation.status"
        ]
        == "success"
    )


class FakeEmbeddings:
    dimension = 3

    async def embed_query(
        self,
        text: str,
    ) -> list[float]:
        assert text

        return [
            1.0,
            0.0,
            0.0,
        ]

    async def embed_documents(
        self,
        texts,
    ) -> list[list[float]]:
        del texts
        return []

    async def close(self) -> None:
        return None


class FakeQdrant:
    async def query_points(
        self,
        **kwargs,
    ):
        del kwargs

        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="point-1",
                    score=0.95,
                    payload={
                        "document_id": "doc-1",
                        "chunk_index": 0,
                        "text": "Internal retrieved text.",
                        "source_path": "docs/private.txt",
                        "file_name": "private.txt",
                        "checksum": "abc",
                        "page_number": None,
                    },
                )
            ]
        )


@pytest.mark.anyio
async def test_rag_creates_nested_safe_span_tree(
    span_exporter: InMemorySpanExporter,
) -> None:
    settings = Settings(
        _env_file=None,
        embedding_dimension=3,
    )

    retriever = SemanticRetriever(
        qdrant=FakeQdrant(),  # type: ignore[arg-type]
        embeddings=FakeEmbeddings(),  # type: ignore[arg-type]
        settings=settings,
    )

    llm = LLMService(
        TraceProvider(),
        metrics_enabled=False,
    )

    service = RAGService(
        retriever=retriever,
        llm_service=llm,
    )

    secret = "PRIVATE_RAG_QUERY_456"

    result = await service.answer(
        secret
    )

    assert result.sources

    spans = {
        span.name: span
        for span in span_exporter.get_finished_spans()
    }

    assert {
        "rag.answer",
        "rag.retrieve",
        "embedding.query",
        "qdrant.search",
        "llm.generate",
    } <= set(spans)

    assert (
        spans["rag.retrieve"].parent.span_id
        == spans["rag.answer"].context.span_id
    )

    assert (
        spans["embedding.query"].parent.span_id
        == spans["rag.retrieve"].context.span_id
    )

    assert (
        spans["qdrant.search"].parent.span_id
        == spans["rag.retrieve"].context.span_id
    )

    assert (
        spans["llm.generate"].parent.span_id
        == spans["rag.answer"].context.span_id
    )

    for span in spans.values():
        assert secret not in str(
            dict(
                span.attributes
            )
        )

        assert (
            "Internal retrieved text."
            not in str(
                dict(
                    span.attributes
                )
            )
        )


class FailingQdrant:
    async def query_points(
        self,
        **kwargs,
    ):
        del kwargs

        raise OSError(
            "simulated qdrant failure"
        )


@pytest.mark.anyio
async def test_qdrant_failure_marks_span_error(
    span_exporter: InMemorySpanExporter,
) -> None:
    retriever = SemanticRetriever(
        qdrant=FailingQdrant(),  # type: ignore[arg-type]
        embeddings=FakeEmbeddings(),  # type: ignore[arg-type]
        settings=Settings(
            _env_file=None,
            embedding_dimension=3,
        ),
    )

    with pytest.raises(
        RetrievalError
    ):
        await retriever.retrieve(
            "safe query"
        )

    qdrant_span = next(
        span
        for span in span_exporter.get_finished_spans()
        if span.name == "qdrant.search"
    )

    assert (
        qdrant_span.status.status_code
        is StatusCode.ERROR
    )

    assert (
        qdrant_span.attributes[
            "error.type"
        ]
        == "RetrievalError"
    )


class NodeExecutingService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback=None,
    ):
        del request_id
        del conversation_id
        del max_hops
        del event_callback

        state = create_initial_state(
            user_query
        )

        async def node(
            node_state,
        ):
            return {
                "active_agent": "general",
                "agent_results": [
                    {
                        "agent": "general",
                        "status": "success",
                    }
                ],
                "hop_count": (
                    node_state["hop_count"]
                    + 1
                ),
            }

        traced_node = _instrument_agent_node(
            "general",
            node,
        )

        update = await traced_node(
            state
        )

        return SimpleNamespace(
            route="general",
            hop_count=update[
                "hop_count"
            ],
        )


@pytest.mark.anyio
async def test_agent_node_is_nested_under_workflow(
    span_exporter: InMemorySpanExporter,
) -> None:
    service = InstrumentedMultiAgentService(
        NodeExecutingService(),
        metrics_enabled=False,
    )

    await service.execute(
        "PRIVATE_AGENT_QUERY",
        max_hops=6,
    )

    spans = {
        span.name: span
        for span in span_exporter.get_finished_spans()
    }

    execution_span = spans[
        "agent.execute"
    ]

    agent_span = spans[
        "agent.general"
    ]

    assert (
        agent_span.parent.span_id
        == execution_span.context.span_id
    )

    assert (
        execution_span.attributes[
            "gen_ai.workflow.name"
        ]
        == "orbyntiq_multi_agent"
    )

    assert (
        agent_span.attributes[
            "gen_ai.agent.name"
        ]
        == "general"
    )

    assert (
        "PRIVATE_AGENT_QUERY"
        not in str(
            dict(
                execution_span.attributes
            )
        )
    )


@pytest.mark.anyio
async def test_failed_agent_node_marks_span_error(
    span_exporter: InMemorySpanExporter,
) -> None:
    async def failed_node(
        state,
    ):
        return {
            "active_agent": "research",
            "agent_results": [
                {
                    "agent": "research",
                    "status": "failed",
                }
            ],
            "hop_count": (
                state["hop_count"]
                + 1
            ),
        }

    node = _instrument_agent_node(
        "research",
        failed_node,
    )

    await node(
        create_initial_state(
            "test"
        )
    )

    span = next(
        item
        for item in span_exporter.get_finished_spans()
        if item.name == "agent.research"
    )

    assert (
        span.status.status_code
        is StatusCode.ERROR
    )

    assert (
        span.attributes[
            "orbyntiq.agent.status"
        ]
        == "failed"
    )


class ToolDecisionService:
    async def chat_structured(
        self,
        prompt: str,
        response_model,
        *,
        system_prompt: str,
        history=(),
    ):
        del prompt
        del response_model
        del system_prompt
        del history

        return MCPToolDecision(
            tool_name="add_numbers",
            arguments={
                "a": 2,
                "b": 3,
            },
            reason="math",
        )


@pytest.mark.anyio
async def test_mcp_tool_call_creates_safe_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    server = MCPServer(
        "trace-mcp"
    )

    @server.tool()
    def add_numbers(
        a: int,
        b: int,
    ) -> dict[str, int]:
        return {
            "result": a + b,
        }

    agent = MCPAgent(
        ToolDecisionService(),  # type: ignore[arg-type]
        server=server,
    )

    state = create_initial_state(
        "Use the math tool."
    )

    update = await agent(
        state
    )

    assert (
        update[
            "agent_results"
        ][0]["status"]
        == "success"
    )

    spans = {
        span.name: span
        for span in span_exporter.get_finished_spans()
    }

    assert "mcp.list_tools" in spans
    assert "mcp.call_tool" in spans

    tool_span = spans[
        "mcp.call_tool"
    ]

    assert (
        tool_span.attributes[
            "gen_ai.tool.name"
        ]
        == "add_numbers"
    )

    assert (
        tool_span.attributes[
            "orbyntiq.mcp.tool.is_error"
        ]
        is False
    )

    attributes = str(
        dict(
            tool_span.attributes
        )
    )

    assert '"a"' not in attributes
    assert '"b"' not in attributes
