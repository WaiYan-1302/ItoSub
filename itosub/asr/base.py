from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from itosub.contracts import ASRSegment

class Transcriber(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def transcribe_file(self, path: str) -> List[ASRSegment]: ...