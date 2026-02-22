from __future__ import annotations
import os
from .base import Translator
from .stub import StubTranslator
from .argos import ArgosTranslator

def get_translator(provider: str | None = None) -> Translator:
    provider = (provider or os.getenv("ITOSUB_TRANSLATOR", "stub")).lower().strip()

    if provider == "stub":
        return StubTranslator()
    if provider == "argos":
        return ArgosTranslator()

    raise ValueError(f"Unknown translator provider: {provider}")