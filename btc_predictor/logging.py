"""Structured logging setup."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any

from btc_predictor.config import RuntimeConfig, load_runtime_config

DEFAULT_LOGGER_NAME = "btc_predictor"


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, sort_keys=True)


def configure_logging(config: RuntimeConfig | None = None) -> logging.Logger:
    """Configure and return the package logger."""

    runtime_config = config or load_runtime_config()
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(runtime_config.log_level)
    logger.propagate = False

    handler = logging.StreamHandler()
    if runtime_config.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"),
        )

    logger.addHandler(handler)
    return logger
