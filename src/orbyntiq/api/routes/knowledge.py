from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)

from orbyntiq.api.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeDocumentsResponse,
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeStatusResponse,
)
from orbyntiq.core.config import get_settings
from orbyntiq.mcp.runtime import get_mcp_services
from orbyntiq.rag.documents import (
    SUPPORTED_DOCUMENT_TYPES,
    DocumentLoadError,
)
from orbyntiq.rag.embeddings import (
    EmbeddingError,
    create_embedding_provider,
)
from orbyntiq.rag.ingestion import (
    DocumentIngestor,
    IngestionError,
)
from orbyntiq.rag.retrieval import (
    RetrievalError,
    RetrievalFilter,
    SemanticRetriever,
)

router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["knowledge"],
)

settings = get_settings()


def _qdrant_from_request(
    request: Request,
) -> AsyncQdrantClient:
    qdrant = getattr(
        request.app.state,
        "qdrant",
        None,
    )

    available = getattr(
        request.app.state,
        "qdrant_available",
        False,
    )

    if qdrant is None or not available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge vector database is unavailable.",
        )

    return qdrant


def _retriever() -> SemanticRetriever:
    services = get_mcp_services()

    if services.retriever is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic retrieval service is unavailable.",
        )

    return services.retriever


def _enum_value(
    value: Any,
) -> str:
    raw = getattr(
        value,
        "value",
        value,
    )

    return str(raw)


async def _scroll_payloads(
    qdrant: AsyncQdrantClient,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    offset = None

    while True:
        records, next_offset = await qdrant.scroll(
            collection_name=settings.qdrant_collection,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for record in records:
            payload = record.payload

            if isinstance(payload, dict):
                payloads.append(payload)

        if next_offset is None:
            break

        offset = next_offset

    return payloads


def _build_document_inventory(
    payloads: list[dict[str, Any]],
) -> list[KnowledgeDocumentResponse]:
    grouped: dict[str, dict[str, Any]] = {}

    page_numbers: dict[
        str,
        set[int],
    ] = defaultdict(set)

    for payload in payloads:
        raw_document_id = payload.get("document_id")

        if raw_document_id is None:
            continue

        document_id = str(raw_document_id)

        if document_id not in grouped:
            grouped[document_id] = {
                "document_id": document_id,
                "file_name": str(
                    payload.get(
                        "file_name",
                        "unknown",
                    )
                ),
                "source_path": str(
                    payload.get(
                        "source_path",
                        "",
                    )
                ),
                "checksum": str(
                    payload.get(
                        "checksum",
                        "",
                    )
                ),
                "chunk_count": 0,
            }

        grouped[document_id]["chunk_count"] += 1

        raw_page = payload.get("page_number")

        if raw_page is not None:
            try:
                page_numbers[document_id].add(int(raw_page))
            except (
                TypeError,
                ValueError,
            ):
                pass

    documents = [
        KnowledgeDocumentResponse(
            document_id=document_id,
            file_name=str(data["file_name"]),
            source_path=str(data["source_path"]),
            checksum=str(data["checksum"]),
            chunk_count=int(data["chunk_count"]),
            page_count=len(page_numbers[document_id]),
        )
        for document_id, data in grouped.items()
    ]

    return sorted(
        documents,
        key=lambda item: (
            item.file_name.casefold(),
            item.document_id,
        ),
    )


@router.get(
    "/status",
    response_model=KnowledgeStatusResponse,
)
async def knowledge_status(
    qdrant: Annotated[
        AsyncQdrantClient,
        Depends(_qdrant_from_request),
    ],
) -> KnowledgeStatusResponse:
    try:
        info = await qdrant.get_collection(settings.qdrant_collection)

        payloads = await _scroll_payloads(qdrant)

    except (
        ResponseHandlingException,
        UnexpectedResponse,
        OSError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to read the knowledge collection.",
        ) from exc

    vectors = info.config.params.vectors

    vector_size = getattr(
        vectors,
        "size",
        settings.embedding_dimension,
    )

    distance = _enum_value(
        getattr(
            vectors,
            "distance",
            "unknown",
        )
    )

    collection_status = _enum_value(
        getattr(
            info,
            "status",
            "unknown",
        )
    )

    documents = _build_document_inventory(payloads)

    return KnowledgeStatusResponse(
        status=collection_status,
        collection=settings.qdrant_collection,
        points_count=int(
            getattr(
                info,
                "points_count",
                len(payloads),
            )
            or 0
        ),
        indexed_vectors_count=int(
            getattr(
                info,
                "indexed_vectors_count",
                0,
            )
            or 0
        ),
        document_count=len(documents),
        vector_size=int(vector_size),
        distance=distance,
        embedding_provider=(settings.embedding_provider),
        embedding_model=(settings.embedding_model),
        embedding_dimension=(settings.embedding_dimension),
        supported_file_types=sorted(SUPPORTED_DOCUMENT_TYPES),
    )


@router.get(
    "/documents",
    response_model=KnowledgeDocumentsResponse,
)
async def list_knowledge_documents(
    qdrant: Annotated[
        AsyncQdrantClient,
        Depends(_qdrant_from_request),
    ],
) -> KnowledgeDocumentsResponse:
    try:
        payloads = await _scroll_payloads(qdrant)

    except (
        ResponseHandlingException,
        UnexpectedResponse,
        OSError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to list knowledge documents.",
        ) from exc

    documents = _build_document_inventory(payloads)

    return KnowledgeDocumentsResponse(
        count=len(documents),
        documents=documents,
    )


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    retriever: Annotated[
        SemanticRetriever,
        Depends(_retriever),
    ],
) -> KnowledgeSearchResponse:
    filters = None

    if request.document_id is not None or request.file_name is not None:
        filters = RetrievalFilter(
            document_id=request.document_id,
            file_name=request.file_name,
        )

    try:
        chunks = await retriever.retrieve(
            request.query,
            limit=request.limit,
            score_threshold=(request.score_threshold),
            filters=filters,
        )

    except (
        RetrievalError,
        EmbeddingError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Knowledge search failed.",
        ) from exc

    return KnowledgeSearchResponse(
        query=request.query,
        count=len(chunks),
        results=[
            KnowledgeSearchResult(
                id=chunk.id,
                score=chunk.score,
                document_id=(chunk.document_id),
                chunk_index=(chunk.chunk_index),
                text=chunk.text,
                source_path=(chunk.source_path),
                file_name=(chunk.file_name),
                checksum=chunk.checksum,
                page_number=(chunk.page_number),
            )
            for chunk in chunks
        ],
    )


@router.post(
    "/ingest",
    response_model=KnowledgeIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_knowledge_document(
    request: Request,
    file_name: Annotated[
        str,
        Query(
            min_length=1,
            max_length=255,
        ),
    ],
    qdrant: Annotated[
        AsyncQdrantClient,
        Depends(_qdrant_from_request),
    ],
) -> KnowledgeIngestResponse:
    safe_name = Path(file_name).name.strip()

    if not safe_name or safe_name != file_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document file name.",
        )

    suffix = Path(safe_name).suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=("Unsupported document type. Supported types are PDF, Markdown, and text."),
        )

    content = await request.body()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded document is empty.",
        )

    if len(content) > settings.knowledge_max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=("Uploaded document exceeds the configured maximum size."),
        )

    storage_dir = Path(settings.knowledge_storage_dir)

    storage_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (storage_dir / safe_name).resolve()

    storage_root = storage_dir.resolve()

    if target.parent != storage_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document destination.",
        )

    try:
        target.write_bytes(content)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store uploaded document.",
        ) from exc

    embedding_provider = create_embedding_provider(settings)

    try:
        ingestor = DocumentIngestor(
            qdrant=qdrant,
            embeddings=embedding_provider,
            settings=settings,
        )

        result = await ingestor.ingest(target)

    except (
        DocumentLoadError,
        IngestionError,
        EmbeddingError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document ingestion failed.",
        ) from exc

    finally:
        await embedding_provider.close()

    return KnowledgeIngestResponse(
        document_id=result.document_id,
        file_name=safe_name,
        checksum=result.checksum,
        chunks_indexed=(result.chunks_indexed),
    )
