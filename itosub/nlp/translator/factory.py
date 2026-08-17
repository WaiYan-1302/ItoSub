from __future__ import annotations
import os
from .base import Translator
from .argos import ArgosTranslator

def get_translator(
    provider: str | None = None,
    *,
    from_code: str = "en",
    to_code: str = "ja",
) -> Translator:
    provider = (provider or os.getenv("ITOSUB_TRANSLATOR", "argos")).lower().strip()

    if provider == "stub":
        # Backward compatibility for old configs; product mode uses Argos only.
        return ArgosTranslator(from_code=from_code, to_code=to_code)
    if provider == "argos":
        return ArgosTranslator(from_code=from_code, to_code=to_code)

    raise ValueError(f"Unknown translator provider: {provider}")
