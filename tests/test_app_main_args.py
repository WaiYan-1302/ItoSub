from __future__ import annotations

import json
from pathlib import Path

from itosub.app.config import resolve_args


def test_app_resolve_args_cli_overrides_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "app.json"
    cfg_path.write_text(
        json.dumps(
            {
                "translator": "stub",
                "sr": 16000,
                "poll_ms": 60,
            }
        ),
        encoding="utf-8",
    )
    args = resolve_args(
        [
            "--config",
            str(cfg_path),
            "--translator",
            "argos",
            "--poll-ms",
            "30",
        ]
    )
    assert args.translator == "argos"
    assert args.sr == 16000
    assert args.poll_ms == 30


def test_app_resolve_args_overlay_controls(tmp_path: Path) -> None:
    cfg_path = tmp_path / "app.json"
    cfg_path.write_text(
        json.dumps({"overlay_opacity": 40, "overlay_position": "bottom_left"}),
        encoding="utf-8",
    )
    args = resolve_args(
        [
            "--config",
            str(cfg_path),
            "--overlay-opacity",
            "75",
            "--overlay-position",
            "top_center",
        ]
    )
    assert args.overlay_opacity == 75
    assert args.overlay_position == "top_center"


def test_app_resolve_args_language_lock(tmp_path: Path) -> None:
    cfg_path = tmp_path / "app.json"
    cfg_path.write_text(
        json.dumps({"language_lock": "auto"}),
        encoding="utf-8",
    )
    args = resolve_args(
        [
            "--config",
            str(cfg_path),
            "--language-lock",
            "en",
        ]
    )
    assert args.language_lock == "en"


def test_app_resolve_args_hotkeys_and_selectable(tmp_path: Path) -> None:
    cfg_path = tmp_path / "app.json"
    cfg_path.write_text(
        json.dumps({"overlay_text_selectable": False, "hotkey_toggle_selectable": "T"}),
        encoding="utf-8",
    )
    args = resolve_args(
        [
            "--config",
            str(cfg_path),
            "--overlay-text-selectable",
            "--hotkey-toggle-selectable",
            "Ctrl+T",
            "--hotkey-toggle-en",
            "Ctrl+E",
        ]
    )
    assert args.overlay_text_selectable is True
    assert args.hotkey_toggle_selectable == "Ctrl+T"
    assert args.hotkey_toggle_en == "Ctrl+E"


def test_app_resolve_args_ui_language(tmp_path: Path) -> None:
    cfg_path = tmp_path / "app.json"
    cfg_path.write_text(
        json.dumps({"ui_language": "en"}),
        encoding="utf-8",
    )
    args = resolve_args(
        [
            "--config",
            str(cfg_path),
            "--ui-language",
            "ja",
        ]
    )
    assert args.ui_language == "ja"

