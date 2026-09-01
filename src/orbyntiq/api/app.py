from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orbyntiq.agents import (
    GeneralAgent,
    MCPAgent,
    ResearchAgent,
    SupervisorAgent,
    SynthesizerAgent,
    build_multi_agent_graph,
)
from orbyntiq.api.dependencies import get_llm_service
from orbyntiq.api.error_handlers import register_error_handlers
from orbyntiq.api.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)
from orbyntiq.api.routes.agents import router as agents_router
from orbyntiq.api.routes.llm import router as llm_router
from orbyntiq.api.routes.websocket import router as websocket_router
from orbyntiq.core.config import get_settings
from orbyntiq.core.logging import configure_logging, get_logger
from orbyntiq.core.mongodb import (
    MongoDBUnavailableError,
    close_mongodb_client,
    create_mongodb_client,
    verify_mongodb_connection,
)
from orbyntiq.core.mongodb_schema import (
    MongoDBSchemaError,
    ensure_mongodb_schema,
)
from orbyntiq.core.qdrant import (
    QdrantUnavailableError,
    close_qdrant_client,
    create_qdrant_client,
    verify_qdrant_connection,
)
from orbyntiq.core.redis import (
    RedisUnavailableError,
    close_redis_client,
    create_redis_client,
    verify_redis_connection,
)
from orbyntiq.mcp.runtime import configure_mcp_services
from orbyntiq.mcp.server import mcp_server
from orbyntiq.observability import (
    MetricsMiddleware,
    TracingMiddleware,
    configure_tracing,
    register_metrics_endpoint,
)
from orbyntiq.observability.agent_metrics import InstrumentedMultiAgentService
from orbyntiq.persistence import (
    AgentExecutionRepository,
    WorkflowHistoryRepository,
)
from orbyntiq.rag.embeddings import create_embedding_provider
from orbyntiq.rag.retrieval import SemanticRetriever
from orbyntiq.rag.service import RAGService
from orbyntiq.services import MultiAgentService

settings = get_settings()

configure_logging()

logger = get_logger(__name__)

mcp_http_app = mcp_server.streamable_http_app(
    streamable_http_path="/",
)



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_client = create_redis_client(settings)
    mongodb_client = create_mongodb_client(settings)
    qdrant_client = create_qdrant_client(settings)

    redis_connected = False
    mongodb_connected = False
    qdrant_connected = False
    embedding_provider = None
    execution_repository = None
    workflow_repository = None

    app.state.redis = None
    app.state.redis_available = False

    app.state.mongodb = None
    app.state.mongodb_database = None
    app.state.mongodb_available = False

    app.state.qdrant = None
    app.state.qdrant_available = False
    app.state.multi_agent_service = None

    configure_mcp_services()

    try:
        try:
            await verify_redis_connection(redis_client)
        except RedisUnavailableError as exc:
            logger.warning(
                "Redis unavailable; application continuing in degraded mode: %s",
                exc,
            )
            await close_redis_client(redis_client)
        else:
            app.state.redis = redis_client
            app.state.redis_available = True
            redis_connected = True

            logger.info("Redis connection established")

        try:
            await verify_mongodb_connection(mongodb_client)
        except MongoDBUnavailableError as exc:
            logger.warning(
                "MongoDB unavailable; application continuing in degraded mode: %s",
                exc,
            )
            await close_mongodb_client(mongodb_client)
        else:
            mongodb_database = mongodb_client[settings.mongodb_database]

            try:
                await ensure_mongodb_schema(mongodb_database)
            except MongoDBSchemaError as exc:
                logger.warning(
                    "MongoDB schema initialization failed; "
                    "application continuing in degraded mode: %s",
                    exc,
                )
                await close_mongodb_client(mongodb_client)
            else:
                app.state.mongodb = mongodb_client
                app.state.mongodb_database = mongodb_database
                app.state.mongodb_available = True
                mongodb_connected = True

                try:
                    execution_repository = (
                        AgentExecutionRepository(
                            mongodb_database
                        )
                    )

                    workflow_repository = (
                        WorkflowHistoryRepository(
                            mongodb_database
                        )
                    )
                except (TypeError, AttributeError) as exc:
                    execution_repository = None
                    workflow_repository = None

                    logger.warning(
                        "Multi-agent persistence repositories "
                        "unavailable; application continuing "
                        "without execution persistence: %s",
                        exc,
                    )

                logger.info("MongoDB connection established")
                logger.info("MongoDB schema initialized")

        try:
            await verify_qdrant_connection(qdrant_client)
        except QdrantUnavailableError as exc:
            logger.warning(
                "Qdrant unavailable; application continuing in degraded mode: %s",
                exc,
            )
            await close_qdrant_client(qdrant_client)
        else:
            app.state.qdrant = qdrant_client
            app.state.qdrant_available = True
            qdrant_connected = True

            logger.info("Qdrant connection established")

            embedding_provider = create_embedding_provider(settings)

            retriever = SemanticRetriever(
                qdrant=qdrant_client,
                embeddings=embedding_provider,
                settings=settings,
            )

            rag_service = RAGService(
                retriever=retriever,
                llm_service=get_llm_service(),
            )

            configure_mcp_services(
                retriever=retriever,
                rag_service=rag_service,
            )

            logger.info("MCP RAG services configured")

            llm_service = get_llm_service()

            graph = build_multi_agent_graph(
                supervisor=SupervisorAgent(llm_service),
                research=ResearchAgent(rag_service),
                mcp=MCPAgent(llm_service),
                general=GeneralAgent(llm_service),
                synthesizer=SynthesizerAgent(llm_service),
            )

            app.state.multi_agent_service = InstrumentedMultiAgentService(
                MultiAgentService(
                    graph,
                    execution_repository=execution_repository,
                    workflow_repository=workflow_repository,
                ),
                metrics_enabled=(
                    settings.observability_enabled
                    and settings.metrics_enabled
                ),
            )

            logger.info("Multi-agent service configured")

        yield
    finally:
        configure_mcp_services()
        app.state.multi_agent_service = None

        if embedding_provider is not None:
            await embedding_provider.close()
            logger.info("Embedding provider closed")

        if qdrant_connected:
            await close_qdrant_client(qdrant_client)
            logger.info("Qdrant connection closed")

        if mongodb_connected:
            await close_mongodb_client(mongodb_client)
            logger.info("MongoDB connection closed")

        if redis_connected:
            await close_redis_client(redis_client)
            logger.info("Redis connection closed")

        app.state.qdrant = None
        app.state.qdrant_available = False

        app.state.mongodb = None
        app.state.mongodb_database = None
        app.state.mongodb_available = False

        app.state.redis = None
        app.state.redis_available = False


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run application services and the MCP transport lifecycle."""
    async with lifespan(app):
        async with mcp_server.session_manager.run():
            yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=application_lifespan,
)

tracer_provider = configure_tracing(settings)

register_metrics_endpoint(app, settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id", "X-Request-ID", "X-Trace-ID"],
)

if (
    settings.observability_enabled
    and settings.metrics_enabled
):
    app.add_middleware(
        MetricsMiddleware,
        metrics_path=settings.metrics_path,
    )

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

if tracer_provider is not None:
    app.add_middleware(
        TracingMiddleware,
        tracer_provider=tracer_provider,
    )

register_error_handlers(app)

app.include_router(agents_router)
app.include_router(llm_router)
app.include_router(websocket_router)


app.mount("/mcp", mcp_http_app, name="mcp")

@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }