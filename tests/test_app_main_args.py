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

