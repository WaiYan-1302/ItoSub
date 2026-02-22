from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence

@dataclass(frozen=True)
class TranslationRequest:
    text: str
    # Optional: recent prior English lines (for context consistency later)
    context: Optional[Sequence[str]] = None
    source_lang: str = "en"
    target_lang: str = "ja"

@dataclass(frozen=True)
class TranslationResult:
    source_text: str
    translated_text: str
    provider: str

@dataclass(frozen=True)
class ASRSegment:
    text: str
    t0: float
    t1: float
    is_final: bool = True  # file mode = final segments
    
@dataclass(frozen=True)
class AudioChunk:
    """
    Raw PCM16 audio chunk captured from a live source (e.g., microphone).
    pcm16: little-endian signed 16-bit PCM bytes (interleaved if channels > 1).
    """
    pcm16: bytes
    sample_rate: int
    channels: int
    start_time: float  # seconds since stream start
    duration: float    # seconds