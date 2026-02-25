from __future__ import annotations

from itosub.contracts import TranslationResult
from itosub.live.live_asr_translate import LiveASRTranslateHandler


class FakeTranslator:
    def __init__(self) -> None:
        self.calls = []

    def translate(self, req):
        self.calls.append(req)
        text = getattr(req, "text", "")
        return TranslationResult(
            source_text=text,
            translated_text=f"JA({text})",
            provider="fake",
        )


def test_live_asr_translate_handler_translates_and_emits():
    translator = FakeTranslator()
    outputs = []
    handler = LiveASRTranslateHandler(
        translator=translator,
        on_commit=lambda t0, t1, en, ja: outputs.append((t0, t1, en, ja)),
    )

    handler.handle_asr(1.25, 2.75, "Hello world")

    assert len(translator.calls) == 1
    assert getattr(translator.calls[0], "text", None) == "Hello world"
    assert outputs == [(1.25, 2.75, "Hello world", "JA(Hello world)")]
