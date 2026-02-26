from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from itosub.app.config import app_paths

_RESERVED_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_FIELDS or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_app_logger(name: str = "itosub.app") -> tuple[logging.Logger, Path, Path]:
    paths = app_paths()
    log_dir = paths.config_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "itosub.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(JsonLineFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
    logger.addHandler(handler)
    return logger, log_dir, log_path

