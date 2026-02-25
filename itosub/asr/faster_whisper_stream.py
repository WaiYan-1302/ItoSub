from __future__ import annotations

import os
import tempfile
import wave
from dataclasses import fields
from typing import List, Optional

from itosub.asr.stream_base import StreamTranscriber
from itosub.contracts import ASRSegment, AudioChunk


from dataclasses import fields
from itosub.contracts import ASRSegment

import math
from array import array

def _pcm16_rms(pcm16: bytes) -> float:
    if not pcm16:
        return 0.0
    a = array("h")
    a.frombytes(pcm16)
    if len(a) == 0:
        return 0.0
    s2 = 0.0
    for v in a:
        fv = float(v)
        s2 += fv * fv
    return math.sqrt(s2 / len(a))

def _make_asr_segment(*, start: float, end: float, text: str) -> ASRSegment:
    """
    Build ASRSegment regardless of whether the project uses (t0,t1) or (start,end).
    """
    names = {f.name for f in fields(ASRSegment)}
    kwargs = {}

    # timestamps
    if "t0" in names:
        kwargs["t0"] = start
    if "t1" in names:
        kwargs["t1"] = end
    if "start" in names:
        kwargs["start"] = start
    if "end" in names:
        kwargs["end"] = end

    # text
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
        min_rms: float = 250.0,  # <-- add
        fallback_disable_thresholds: bool = True,  # <-- add
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.min_rms = float(min_rms)
        self.fallback_disable_thresholds = bool(fallback_disable_thresholds)

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
        # Energy gate: don't transcribe near-silence (prevents hallucinations)
        rms = _pcm16_rms(chunk.pcm16)
        if rms < self.min_rms:
            return []

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

            # Pass 1: normal / conservative (reduces garbage)
            segments, _info = model.transcribe(
                tmp_path,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=False,
                condition_on_previous_text=False,
                temperature=0.0,
                best_of=1,
            )

            seg_list = list(segments)

            # Pass 2 (fallback): if loud but got nothing, relax thresholds once
            if self.fallback_disable_thresholds and len(seg_list) == 0:
                segments2, _info2 = model.transcribe(
                    tmp_path,
                    language=self.language,
                    beam_size=self.beam_size,
                    vad_filter=False,
                    condition_on_previous_text=False,
                    temperature=0.0,
                    best_of=1,
                    no_speech_threshold=None,
                    log_prob_threshold=None,
                    compression_ratio_threshold=None,
                )
                seg_list = list(segments2)

            out: List[ASRSegment] = []
            for s in seg_list:
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