from __future__ import annotations

import os
import tempfile
import wave
from dataclasses import fields
from typing import List, Optional

from itosub.asr.stream_base import StreamTranscriber
from itosub.contracts import ASRSegment, AudioChunk


def _make_asr_segment(*, start: float, end: float, text: str) -> ASRSegment:
    """
    Construct ASRSegment safely even if your dataclass has extra fields.
    Assumes it has at least (start, end, text) or a subset thereof.
    """
    names = {f.name for f in fields(ASRSegment)}
    kwargs = {}
    if "start" in names:
        kwargs["start"] = start
    if "end" in names:
        kwargs["end"] = end
    if "text" in names:
        kwargs["text"] = text
    return ASRSegment(**kwargs)  # type: ignore[arg-type]


def _write_pcm16_wav(path: str, pcm16: bytes, sample_rate: int, channels: int) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)


class FasterWhisperStreamTranscriber(StreamTranscriber):
    """
    Simple Milestone-4 approach:
    - treat each chunk as final
    - write chunk to a temp WAV
    - call faster-whisper WhisperModel.transcribe(path)
    """

    def __init__(
        self,
        *,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
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

    def transcribe_chunk(self, chunk: AudioChunk) -> List[ASRSegment]:
        model = self._get_model()

        fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="itosub_mic_")
        os.close(fd)
        try:
            _write_pcm16_wav(
                tmp_path,
                chunk.pcm16,
                sample_rate=chunk.sample_rate,
                channels=chunk.channels,
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
                # s.start / s.end are relative to the temp WAV (i.e., chunk-local)
                out.append(
                    _make_asr_segment(
                        start=chunk.start_time + float(s.start),
                        end=chunk.start_time + float(s.end),
                        text=str(s.text).strip(),
                    )
                )
            return out
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass