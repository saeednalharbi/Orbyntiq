from typing import Any

from mcp.server import MCPServer

from orbyntiq.mcp.runtime import get_mcp_services
from orbyntiq.rag.retrieval import RetrievalFilter

mcp_server = MCPServer("orbyntiq")


def _build_filter(
    *,
    document_id: str | None = None,
    file_name: str | None = None,
) -> RetrievalFilter | None:
    if document_id is None and file_name is None:
        return None

    return RetrievalFilter(
        document_id=document_id,
        file_name=file_name,
    )


@mcp_server.tool()
def platform_status() -> dict[str, Any]:
    """Return the current Orbyntiq MCP platform status."""
    services = get_mcp_services()

    return {
        "service": "orbyntiq-mcp",
        "status": "ok",
        "protocol": "mcp",
        "retriever_configured": services.retriever is not None,
        "rag_configured": services.rag_service is not None,
    }


@mcp_server.tool()
async def search_knowledge(
    query: str,
    limit: int = 5,
    score_threshold: float | None = None,
    document_id: str | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    """Search the Orbyntiq vector knowledge base for relevant chunks."""
    services = get_mcp_services()

    if services.retriever is None:
        raise RuntimeError("MCP semantic retriever is not configured")

    filters = _build_filter(
        document_id=document_id,
        file_name=file_name,
    )

    chunks = await services.retriever.retrieve(
        query,
        limit=limit,
        score_threshold=score_threshold,
        filters=filters,
    )

    return {
        "query": query,
        "count": len(chunks),
        "results": [
            {
                "id": chunk.id,
                "score": chunk.score,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "source_path": chunk.source_path,
                "file_name": chunk.file_name,
                "checksum": chunk.checksum,
                "page_number": chunk.page_number,
            }
            for chunk in chunks
        ],
    }


@mcp_server.tool()
async def answer_with_rag(
    question: str,
    limit: int = 5,
    score_threshold: float | None = 0.25,
    document_id: str | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    """Answer a question using Orbyntiq retrieval-augmented generation."""
    services = get_mcp_services()

    if services.rag_service is None:
        raise RuntimeError("MCP RAG service is not configured")

    filters = _build_filter(
        document_id=document_id,
        file_name=file_name,
    )

    result = await services.rag_service.answer(
        question,
        limit=limit,
        score_threshold=score_threshold,
        filters=filters,
    )

    return {
        "question": question,
        "answer": result.answer,
        "model": result.model,
        "sources": [
            {
                "citation": source.citation,
                "document_id": source.document_id,
                "file_name": source.file_name,
                "source_path": source.source_path,
                "chunk_index": source.chunk_index,
                "score": source.score,
                "page_number": source.page_number,
            }
            for source in result.sources
        ],
    }


@mcp_server.resource("orbyntiq://platform/info")
def platform_info() -> str:
    """Return basic information about the Orbyntiq platform."""
    return (
        "Orbyntiq is an enterprise multi-agent AI platform. "
        "Its MCP service exposes platform capabilities to MCP-compatible clients."
    )


@mcp_server.prompt()
def rag_assistant(question: str) -> str:
    """Create a grounded RAG assistant prompt."""
    return (
        "Answer the user's question using retrieved Orbyntiq knowledge. "
        "Do not invent information that is not supported by retrieved context.\n\n"
        f"Question: {question}"
    )


def get_mcp_server() -> MCPServer:
    """Return the Orbyntiq MCP server instance."""
    return mcp_server
