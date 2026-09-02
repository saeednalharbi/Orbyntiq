from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
)

KnowledgeQuery = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20_000,
    ),
]


OptionalFilterText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=1_024,
    ),
]


class KnowledgeStatusResponse(BaseModel):
    status: str
    collection: str
    points_count: int
    indexed_vectors_count: int
    document_count: int
    vector_size: int
    distance: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    supported_file_types: list[str]


class KnowledgeDocumentResponse(BaseModel):
    document_id: str
    file_name: str
    source_path: str
    checksum: str
    chunk_count: int
    page_count: int


class KnowledgeDocumentsResponse(BaseModel):
    count: int
    documents: list[KnowledgeDocumentResponse]


class KnowledgeSearchRequest(BaseModel):
    query: KnowledgeQuery
    limit: int = Field(
        default=5,
        ge=1,
        le=50,
    )
    score_threshold: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
    )
    document_id: OptionalFilterText | None = None
    file_name: OptionalFilterText | None = None


class KnowledgeSearchResult(BaseModel):
    id: str
    score: float
    document_id: str
    chunk_index: int
    text: str
    source_path: str
    file_name: str
    checksum: str
    page_number: int | None = None


class KnowledgeSearchResponse(BaseModel):
    query: str
    count: int
    results: list[KnowledgeSearchResult]


class KnowledgeIngestResponse(BaseModel):
    document_id: str
    file_name: str
    checksum: str
    chunks_indexed: int
