from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from itosub.contracts import ASRSegment, AudioChunk


class StreamTranscriber(ABC):
    @abstractmethod
    def transcribe_chunk(self, chunk: AudioChunk) -> List[ASRSegment]:
        """Return ASR segments with timestamps in the same global timeline as chunk.start_time."""
        raise NotImplementedError