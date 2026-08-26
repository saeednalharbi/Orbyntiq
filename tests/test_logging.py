import json
import logging

from orbyntiq.core.logging import JsonFormatter, configure_logging


def test_json_formatter():
    formatter = JsonFormatter()

    record = logging.LogRecord(
        name="orbyntiq.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    result = json.loads(formatter.format(record))

    assert result["level"] == "INFO"
    assert result["logger"] == "orbyntiq.test"
    assert result["message"] == "Test message"
    assert "timestamp" in result


def test_configure_logging():
    configure_logging("DEBUG")

    root_logger = logging.getLogger()

    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0].formatter, JsonFormatter)