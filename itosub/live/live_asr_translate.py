from __future__ import annotations

from dataclasses import fields
from typing import Callable, Protocol

from itosub.contracts import TranslationRequest


class Translator(Protocol):
    def translate(self, req: TranslationRequest):
        ...


def _make_translation_request(text: str) -> TranslationRequest:
    names = {f.name for f in fields(TranslationRequest)}
    kwargs = {}
    if "text" in names:
        kwargs["text"] = text
    if "source_lang" in names:
        kwargs["source_lang"] = "en"
    if "target_lang" in names:
        kwargs["target_lang"] = "ja"
    return TranslationRequest(**kwargs)  # type: ignore[arg-type]


class LiveASRTranslateHandler:
    """
    Handle finalized ASR utterances and emit translated lines.
    """

    def __init__(
        self,
        *,
        translator: Translator,
        on_commit: Callable[[float, float, str, str], None],  # (t0, t1, en, ja)
    ) -> None:
        self.translator = translator
        self.on_commit = on_commit

    def handle_asr(self, t0: float, t1: float, text: str) -> None:
        en = (text or "").strip()
        if not en:
            return
        req = _make_translation_request(en)
        res = self.translator.translate(req)
        ja = getattr(res, "translated_text", None) or getattr(res, "text", None) or str(res)
        self.on_commit(float(t0), float(t1), en, str(ja))
