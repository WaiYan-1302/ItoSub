from __future__ import annotations
from typing import List, Optional
from faster_whisper import WhisperModel
from .base import Transcriber
from itosub.contracts import ASRSegment

class FasterWhisperFileTranscriber(Transcriber):
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",  # good default for CPU
        language: Optional[str] = "en",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Optional[WhisperModel] = None

    @property
    def name(self) -> str:
        return "faster-whisper"

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe_file(self, path: str) -> List[ASRSegment]:
        model = self._get_model()
        segments, info = model.transcribe(
            path,
            language=self.language,
            vad_filter=False,   # streaming/VAD comes later (milestone 5)
        )

        out: List[ASRSegment] = []
        for s in segments:
            text = (s.text or "").strip()
            if text:
                out.append(ASRSegment(text=text, t0=float(s.start), t1=float(s.end), is_final=True))
        return out