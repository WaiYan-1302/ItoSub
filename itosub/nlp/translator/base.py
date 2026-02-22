from __future__ import annotations
from abc import ABC, abstractmethod
from itosub.contracts import TranslationRequest, TranslationResult

class Translator(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def translate(self, req: TranslationRequest) -> TranslationResult: ...