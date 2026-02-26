from __future__ import annotations

import json
import logging
from pathlib import Path

from itosub.app import config as app_config
from itosub.app.logging_setup import setup_app_logger


def test_setup_app_logger_writes_json_line(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_config, "user_config_dir", lambda appname, appauthor=None: str(tmp_path))
    logger, log_dir, log_path = setup_app_logger("itosub.test")

    logger.info("hello", extra={"event": "test_event", "value": 7})
    for h in logger.handlers:
        h.flush()

    assert log_dir.exists()
    assert log_path.exists()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["message"] == "hello"
    assert payload["event"] == "test_event"
    assert payload["value"] == 7
    assert payload["level"] == "INFO"

    for h in logger.handlers:
        h.close()
    logging.getLogger("itosub.test").handlers.clear()

