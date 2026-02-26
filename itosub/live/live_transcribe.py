from __future__ import annotations

from typing import Callable, Iterable

from itosub.asr.faster_whisper_pcm16 import FasterWhisperPCM16Transcriber
from itosub.audio.vad import EnergyVAD, pcm16_rms
from itosub.contracts import AudioChunk


class LiveUtteranceTranscriber:
    def __init__(
        self,
        *,
        chunk_iter: Iterable[AudioChunk],
        transcriber: FasterWhisperPCM16Transcriber,
        vad: EnergyVAD,
        on_asr: Callable[[float, float, str], None],
        silence_chunks_to_finalize: int = 2,
        silence_chunks: int | None = None,
        min_utter_sec: float = 0.6,
        max_utter_sec: float | None = None,
        debug: bool = False,
    ) -> None:
        if silence_chunks is not None:
            silence_chunks_to_finalize = silence_chunks
        if silence_chunks_to_finalize <= 0:
            raise ValueError("silence_chunks_to_finalize must be > 0")
        if min_utter_sec < 0:
            raise ValueError("min_utter_sec must be >= 0")
        if max_utter_sec is not None and max_utter_sec <= 0:
            raise ValueError("max_utter_sec must be > 0 when set")

        self.chunk_iter = chunk_iter
        self.transcriber = transcriber
        self.vad = vad
        self.on_asr = on_asr
        self.silence_chunks_to_finalize = int(silence_chunks_to_finalize)
        self.min_utter_sec = float(min_utter_sec)
        self.max_utter_sec = float(max_utter_sec) if max_utter_sec is not None else None
        self.debug = debug

    @staticmethod
    def _duration_from_pcm16(pcm16: bytes, sample_rate: int, channels: int) -> float:
        bytes_per_second = sample_rate * channels * 2
        if bytes_per_second <= 0:
            return 0.0
        return len(pcm16) / float(bytes_per_second)

    def _finalize_utterance(
        self,
        utter_pcm16: bytes,
        utter_sr: int,
        utter_ch: int,
        utter_t0: float,
        reason: str,
    ) -> None:
        utter_sec = self._duration_from_pcm16(utter_pcm16, utter_sr, utter_ch)
        if utter_sec < self.min_utter_sec:
            if self.debug:
                print(
                    f"[debug] finalize skipped short utterance "
                    f"reason={reason} t0={utter_t0:.2f}s dur={utter_sec:.2f}s"
                )
            return

        segments = self.transcriber.transcribe_utterance(
            utter_pcm16,
            sample_rate=utter_sr,
            channels=utter_ch,
            utter_t0=utter_t0,
        )
        if self.debug:
            print(
                f"[debug] finalize utterance reason={reason} "
                f"t0={utter_t0:.2f}s dur={utter_sec:.2f}s "
                f"segments={len(segments)}"
            )
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            self.on_asr(float(seg.t0), float(seg.t1), text)

    def run(self) -> None:
        utter_parts: list[bytes] = []
        utter_t0 = 0.0
        utter_sr = 0
        utter_ch = 0
        in_utterance = False
        trailing_silence = 0
        utter_bytes = 0

        for i, chunk in enumerate(self.chunk_iter, start=1):
            rms = pcm16_rms(chunk.pcm16)
            is_speech = self.vad.is_speech(chunk.pcm16)

            if self.debug:
                chunk_t1 = chunk.start_time + chunk.duration
                print(
                    f"[debug] chunk#{i} {chunk.start_time:.2f}-{chunk_t1:.2f}s "
                    f"rms={rms:.1f} speech={is_speech}"
                )

            if is_speech:
                if not in_utterance:
                    in_utterance = True
                    utter_parts = []
                    utter_bytes = 0
                    utter_t0 = float(chunk.start_time)
                    utter_sr = int(chunk.sample_rate)
                    utter_ch = int(chunk.channels)

                utter_parts.append(chunk.pcm16)
                utter_bytes += len(chunk.pcm16)
                trailing_silence = 0
                if self.max_utter_sec is not None:
                    bytes_per_second = utter_sr * utter_ch * 2
                    utter_sec = (utter_bytes / float(bytes_per_second)) if bytes_per_second > 0 else 0.0
                    if utter_sec >= self.max_utter_sec:
                        self._finalize_utterance(
                            utter_pcm16=b"".join(utter_parts),
                            utter_sr=utter_sr,
                            utter_ch=utter_ch,
                            utter_t0=utter_t0,
                            reason="max_utter_sec",
                        )
                        in_utterance = False
                        trailing_silence = 0
                        utter_parts = []
                        utter_bytes = 0
                continue

            if in_utterance:
                trailing_silence += 1
                if trailing_silence >= self.silence_chunks_to_finalize:
                    self._finalize_utterance(
                        utter_pcm16=b"".join(utter_parts),
                        utter_sr=utter_sr,
                        utter_ch=utter_ch,
                        utter_t0=utter_t0,
                        reason="silence",
                    )
                    in_utterance = False
                    trailing_silence = 0
                    utter_parts = []
                    utter_bytes = 0

        if in_utterance and utter_parts:
            self._finalize_utterance(
                utter_pcm16=b"".join(utter_parts),
                utter_sr=utter_sr,
                utter_ch=utter_ch,
                utter_t0=utter_t0,
                reason="stream_end",
            )
