from __future__ import annotations

from argparse import Namespace

from itosub.app import services as app_services


def _args(language_lock: str) -> Namespace:
    return Namespace(
        chunk_sec=0.5,
        sr=16000,
        channels=1,
        device=None,
        rms_th=180.0,
        model="base",
        language_lock=language_lock,
        translator="stub",
        gap_sec=0.8,
        hard_max_chars=120,
    )


def test_build_services_asr_language_auto(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeTranscriber:
        def __init__(self, *, model_size: str, language):
            captured["model_size"] = model_size
            captured["language"] = language

    monkeypatch.setattr(app_services, "FasterWhisperPCM16Transcriber", _FakeTranscriber)
    app_services.build_live_overlay_services(_args("auto"))
    assert captured["model_size"] == "base"
    assert captured["language"] is None


def test_build_services_asr_language_en(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeTranscriber:
        def __init__(self, *, model_size: str, language):
            captured["model_size"] = model_size
            captured["language"] = language

    monkeypatch.setattr(app_services, "FasterWhisperPCM16Transcriber", _FakeTranscriber)
    app_services.build_live_overlay_services(_args("en"))
    assert captured["model_size"] == "base"
    assert captured["language"] == "en"
