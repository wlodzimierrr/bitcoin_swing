import json
import logging

from btc_predictor.config import RuntimeConfig
from btc_predictor.logging import JsonFormatter, configure_logging


def test_configure_logging_returns_package_logger() -> None:
    config = RuntimeConfig(
        environment="test",
        app_name="bitcoin-swing-predictor",
        log_level="WARNING",
        log_format="json",
    )

    logger = configure_logging(config)

    assert logger.name == "btc_predictor"
    assert logger.level == logging.WARNING
    assert len(logger.handlers) == 1


def test_json_formatter_outputs_structured_log() -> None:
    record = logging.LogRecord(
        name="btc_predictor.tests",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "btc_predictor.tests"
    assert payload["message"] == "hello"
    assert "timestamp" in payload
