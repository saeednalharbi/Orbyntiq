from typing import Any

import pytest
from mcp import Client

from orbyntiq.mcp.runtime import configure_mcp_services
from orbyntiq.mcp.server import get_mcp_server, mcp_server
from orbyntiq.rag.retrieval import RetrievedChunk
from orbyntiq.rag.service import RAGAnswer, RAGSource


class FakeRetriever:
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        filters: Any = None,
    ) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                id="chunk-1",
                score=0.91,
                document_id="doc-1",
                chunk_index=0,
                text=f"Relevant information for {query}",
                source_path="docs/example.txt",
                file_name="example.txt",
                checksum="abc123",
                page_number=None,
            )
        ]


class FakeRAGService:
    async def answer(
        self,
        question: str,
        *,
        limit: int = 5,
        score_threshold: float | None = 0.25,
        filters: Any = None,
    ) -> RAGAnswer:
        return RAGAnswer(
            answer=f"Grounded answer for {question}",
            sources=(
                RAGSource(
                    citation="[1]",
                    document_id="doc-1",
                    file_name="example.txt",
                    source_path="docs/example.txt",
                    chunk_index=0,
                    score=0.91,
                    page_number=None,
                ),
            ),
            model="test-model",
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def configure_services() -> None:
    configure_mcp_services(
        retriever=FakeRetriever(),  # type: ignore[arg-type]
        rag_service=FakeRAGService(),  # type: ignore[arg-type]
    )


def test_get_mcp_server_returns_server() -> None:
    assert get_mcp_server() is mcp_server


@pytest.mark.anyio
async def test_expected_mcp_primitives_are_registered() -> None:
    async with Client(mcp_server) as client:
        tool_names = {tool.name for tool in (await client.list_tools()).tools}
        resource_uris = {
            str(resource.uri)
            for resource in (await client.list_resources()).resources
        }
        prompt_names = {
            prompt.name
            for prompt in (await client.list_prompts()).prompts
        }

    assert {
        "platform_status",
        "search_knowledge",
        "answer_with_rag",
    } <= tool_names

    assert "orbyntiq://platform/info" in resource_uris
    assert "rag_assistant" in prompt_names


@pytest.mark.anyio
async def test_platform_status_tool() -> None:
    async with Client(mcp_server) as client:
        result = await client.call_tool("platform_status", {})

    assert not result.is_error
    text = result.content[0].text.replace(" ", "")
    assert '"status":"ok"' in text
    assert '"retriever_configured":true' in text
    assert '"rag_configured":true' in text


@pytest.mark.anyio
async def test_search_knowledge_tool() -> None:
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "search_knowledge",
            {
                "query": "What is MCP?",
                "limit": 3,
            },
        )

    assert not result.is_error

    text = result.content[0].text
    assert "Relevant information for What is MCP?" in text
    assert "example.txt" in text
    assert "0.91" in text


@pytest.mark.anyio
async def test_answer_with_rag_tool() -> None:
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "answer_with_rag",
            {
                "question": "What is vector search?",
            },
        )

    assert not result.is_error

    text = result.content[0].text
    assert "Grounded answer for What is vector search?" in text
    assert "test-model" in text
    assert "example.txt" in text


@pytest.mark.anyio
async def test_platform_info_resource() -> None:
    async with Client(mcp_server) as client:
        result = await client.read_resource("orbyntiq://platform/info")

    assert "enterprise multi-agent AI platform" in result.contents[0].text


@pytest.mark.anyio
async def test_rag_assistant_prompt() -> None:
    async with Client(mcp_server) as client:
        result = await client.get_prompt(
            "rag_assistant",
            {"question": "What is vector search?"},
        )

    text = result.messages[0].content.text
    assert "retrieved Orbyntiq knowledge" in text
    assert "What is vector search?" in text
