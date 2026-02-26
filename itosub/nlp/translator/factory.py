from __future__ import annotations
import os
from .base import Translator
from .argos import ArgosTranslator

def get_translator(provider: str | None = None) -> Translator:
    provider = (provider or os.getenv("ITOSUB_TRANSLATOR", "argos")).lower().strip()

    if provider == "stub":
        # Backward compatibility for old configs; product mode uses Argos only.
        return ArgosTranslator()
    if provider == "argos":
        return ArgosTranslator()

    raise ValueError(f"Unknown translator provider: {provider}")
