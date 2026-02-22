from __future__ import annotations
from .base import Translator
from itosub.contracts import TranslationRequest, TranslationResult

class StubTranslator(Translator):
    @property
    def name(self) -> str:
        return "stub"

    def translate(self, req: TranslationRequest) -> TranslationResult:
        # Deterministic, test-friendly
        ja = f"【仮訳（かやく / kayaku）】{req.text}"
        return TranslationResult(source_text=req.text, translated_text=ja, provider=self.name)