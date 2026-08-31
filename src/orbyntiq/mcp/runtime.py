"""Runtime dependencies used by Orbyntiq MCP tools."""

from dataclasses import dataclass

from orbyntiq.rag.retrieval import SemanticRetriever
from orbyntiq.rag.service import RAGService


@dataclass
class MCPServices:
    """Runtime services exposed through MCP."""

    retriever: SemanticRetriever | None = None
    rag_service: RAGService | None = None


_services = MCPServices()


def configure_mcp_services(
    *,
    retriever: SemanticRetriever | None = None,
    rag_service: RAGService | None = None,
) -> None:
    """Configure runtime services used by MCP tools."""
    _services.retriever = retriever
    _services.rag_service = rag_service


def get_mcp_services() -> MCPServices:
    """Return the current MCP runtime services."""
    return _services
