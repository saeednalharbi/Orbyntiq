from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orbyntiq.llm.errors import (
    LLMConnectionError,
    LLMHTTPError,
    LLMInvalidResponseError,
    LLMModelNotFoundError,
    LLMTimeoutError,
)
from orbyntiq.services import (
    MultiAgentExecutionError,
    MultiAgentUnavailableError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LLMTimeoutError)
    async def llm_timeout_handler(
        request: Request,
        exc: LLMTimeoutError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content={"detail": "The local LLM timed out."},
        )

    @app.exception_handler(LLMConnectionError)
    async def llm_connection_handler(
        request: Request,
        exc: LLMConnectionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "The local LLM service is unavailable."},
        )

    @app.exception_handler(LLMModelNotFoundError)
    async def llm_model_handler(
        request: Request,
        exc: LLMModelNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "The configured local LLM model is unavailable."
                )
            },
        )

    @app.exception_handler(LLMHTTPError)
    async def llm_http_handler(
        request: Request,
        exc: LLMHTTPError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "detail": "The local LLM returned an upstream error."
            },
        )

    @app.exception_handler(LLMInvalidResponseError)
    async def llm_invalid_response_handler(
        request: Request,
        exc: LLMInvalidResponseError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "detail": "The local LLM returned an invalid response."
            },
        )

    @app.exception_handler(MultiAgentUnavailableError)
    async def multi_agent_unavailable_handler(
        request: Request,
        exc: MultiAgentUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "The multi-agent service is unavailable."
            },
        )

    @app.exception_handler(MultiAgentExecutionError)
    async def multi_agent_execution_handler(
        request: Request,
        exc: MultiAgentExecutionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "The multi-agent execution failed."
            },
        )
