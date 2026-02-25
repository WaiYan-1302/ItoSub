from __future__ import annotations

import json

from itosub.demos.demo_live_mic_transcribe import _resolve_args


def test_config_defaults_are_loaded_and_cli_overrides(tmp_path):
    cfg_path = tmp_path / "live.json"
    cfg_path.write_text(
        json.dumps(
            {
                "device": 1,
                "sr": 48000,
                "channels": 1,
                "chunk_sec": 0.6,
                "rms_th": 140.0,
                "silence_chunks": 3,
                "min_utter_sec": 0.6,
                "max_utter_sec": 5.0,
                "model": "base",
                "debug": True,
            }
        ),
        encoding="utf-8",
    )

    args = _resolve_args(["--config", str(cfg_path), "--rms-th", "180", "--model", "tiny"])

    assert args.device == 1
    assert args.sr == 48000
    assert args.chunk_sec == 0.6
    assert args.silence_chunks == 3
    assert args.min_utter_sec == 0.6
    assert args.max_utter_sec == 5.0
    assert args.rms_th == 180.0
    assert args.model == "tiny"
    assert args.debug is True
