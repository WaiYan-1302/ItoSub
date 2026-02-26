from __future__ import annotations

import json
from pathlib import Path

from itosub.app import config as app_config


def test_load_default_config_contains_expected_keys() -> None:
    cfg = app_config.load_default_config()
    assert cfg["translator"] in {"stub", "argos"}
    assert "poll_ms" in cfg
    assert "gap_sec" in cfg


def test_resolve_defaults_uses_explicit_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "explicit.json"
    cfg_path.write_text(json.dumps({"sr": 16000, "model": "tiny"}), encoding="utf-8")
    defaults, used = app_config.resolve_defaults(str(cfg_path))
    assert used == cfg_path
    assert defaults["sr"] == 16000
    assert defaults["model"] == "tiny"


def test_ensure_user_config_exists_creates_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_config, "user_config_dir", lambda appname, appauthor=None: str(tmp_path))
    created = app_config.ensure_user_config_exists({"translator": "stub", "sr": 16000})
    assert created.exists()
    loaded = json.loads(created.read_text(encoding="utf-8"))
    assert loaded["translator"] == "stub"
    assert loaded["sr"] == 16000


def test_load_user_config_ignores_unknown_keys(tmp_path: Path) -> None:
    cfg_path = tmp_path / "user.json"
    cfg_path.write_text(
        json.dumps({"sr": 48000, "translator": "argos", "unexpected": 1}),
        encoding="utf-8",
    )
    loaded, used = app_config.load_user_config(str(cfg_path))
    assert used == cfg_path
    assert loaded["sr"] == 48000
    assert loaded["translator"] == "argos"
    assert "unexpected" not in loaded


def test_save_user_config_merges_and_filters_keys(tmp_path: Path) -> None:
    cfg_path = tmp_path / "user.json"
    cfg_path.write_text(
        json.dumps({"sr": 16000, "translator": "stub", "debug": False}),
        encoding="utf-8",
    )
    saved = app_config.save_user_config(
        {"translator": "argos", "poll_ms": 30, "junk": "x"},
        config_path=str(cfg_path),
    )
    assert saved == cfg_path
    loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert loaded["sr"] == 16000
    assert loaded["translator"] == "argos"
    assert loaded["poll_ms"] == 30
    assert "junk" not in loaded
