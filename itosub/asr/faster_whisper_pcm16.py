from __future__ import annotations

import os
import tempfile
import wave
from typing import List, Optional

from itosub.contracts import ASRSegment


def _write_pcm16_wav(path: str, pcm16: bytes, sample_rate: int, channels: int) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)


class FasterWhisperPCM16Transcriber:
    def __init__(
        self,
        *,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = "en",
        beam_size: int = 1,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe_utterance(
        self,
        pcm16: bytes,
        sample_rate: int,
        channels: int,
        utter_t0: float,
    ) -> List[ASRSegment]:
        if not pcm16:
            return []

        model = self._get_model()

        fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="itosub_utter_")
        os.close(fd)
        try:
            _write_pcm16_wav(
                tmp_path,
                pcm16,
                sample_rate=sample_rate,
                channels=channels,
            )
            segments, _info = model.transcribe(
                tmp_path,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=False,
                condition_on_previous_text=False,
            )

            out: List[ASRSegment] = []
            for s in segments:
                text = (s.text or "").strip()
                if not text:
                    continue
                out.append(
                    ASRSegment(
                        text=text,
                        t0=float(utter_t0 + float(s.start)),
                        t1=float(utter_t0 + float(s.end)),
                        is_final=True,
                    )
                )
            return out
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
