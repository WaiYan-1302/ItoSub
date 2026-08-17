from __future__ import annotations

from argparse import Namespace

from itosub.app import services as app_services


def _args(language_lock: str, caption_language: str = "en") -> Namespace:
    return Namespace(
        chunk_sec=0.5,
        sr=16000,
        channels=1,
        device=None,
        rms_th=180.0,
        model="base",
        language_lock=language_lock,
        caption_language=caption_language,
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


def test_build_services_japanese_caption_direction(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeTranscriber:
        def __init__(self, *, model_size: str, language):
            captured["language"] = language

    def _fake_get_translator(provider: str, *, from_code: str, to_code: str):
        captured["provider"] = provider
        captured["from_code"] = from_code
        captured["to_code"] = to_code
        return object()

    monkeypatch.setattr(app_services, "FasterWhisperPCM16Transcriber", _FakeTranscriber)
    monkeypatch.setattr(app_services, "get_translator", _fake_get_translator)
    app_services.build_live_overlay_services(_args("auto", caption_language="ja"))

    assert captured["language"] == "ja"
    assert captured["from_code"] == "ja"
    assert captured["to_code"] == "en"
