import json
import logging
from datetime import UTC, datetime

from opentelemetry import trace

from orbyntiq.core.config import get_settings
from orbyntiq.core.request_context import get_request_id

STRUCTURED_LOG_FIELDS = (
    "event",
    "http_method",
    "http_path",
    "http_status_code",
    "duration_ms",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()

        if request_id is not None:
            log_entry["request_id"] = request_id

        span_context = (
            trace.get_current_span().get_span_context()
        )

        if span_context.is_valid:
            log_entry["trace_id"] = format(
                span_context.trace_id,
                "032x",
            )
            log_entry["span_id"] = format(
                span_context.span_id,
                "016x",
            )

        for field in STRUCTURED_LOG_FIELDS:
            value = getattr(record, field, None)

            if value is not None:
                log_entry[field] = value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def configure_logging(level: str | None = None) -> None:
    settings = get_settings()
    log_level = level or settings.log_level

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
