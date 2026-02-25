from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Iterable, Iterator

from itosub.audio.vad_webrtc import WebRtcVad
from itosub.contracts import AudioChunk


@dataclass(frozen=True)
class UtteranceConfig:
    frame_ms: int = 20
    vad_aggressiveness: int = 2
    min_speech_ms: int = 200
    end_silence_ms: int = 500


def _iter_vad_frames(chunk: AudioChunk, frame_bytes: int) -> Iterator[bytes]:
    pcm16 = chunk.pcm16
    for i in range(0, len(pcm16) - frame_bytes + 1, frame_bytes):
        yield pcm16[i : i + frame_bytes]


def _to_mono_pcm16(frame: bytes, channels: int) -> bytes:
    if channels <= 1:
        return frame
    samples = array("h")
    samples.frombytes(frame)
    mono = array("h")
    for i in range(0, len(samples), channels):
        mono.append(samples[i])
    return mono.tobytes()


def utterances_from_audio_chunks(
    chunks: Iterable[AudioChunk],
    cfg: UtteranceConfig,
) -> Iterator[AudioChunk]:
    """
    Group AudioChunk stream into utterance AudioChunks using WebRTC VAD on fixed frames.
    Output utterances are mono PCM16.
    """
    vad: WebRtcVad | None = None
    frame_dur = cfg.frame_ms / 1000.0
    min_speech_frames = max(1, cfg.min_speech_ms // cfg.frame_ms)
    end_silence_frames = max(1, cfg.end_silence_ms // cfg.frame_ms)

    in_utt = False
    speech_frames = 0
    silence_run = 0
    utter_pcm_parts: list[bytes] = []
    utter_t0 = 0.0
    utter_t1 = 0.0
    utter_sr = 0

    def maybe_emit() -> AudioChunk | None:
        nonlocal in_utt, speech_frames, silence_run, utter_pcm_parts, utter_t0, utter_t1
        if not in_utt:
            return None
        in_utt = False
        silence_run = 0
        if speech_frames < min_speech_frames or not utter_pcm_parts:
            speech_frames = 0
            utter_pcm_parts = []
            return None
        pcm16 = b"".join(utter_pcm_parts)
        out = AudioChunk(
            pcm16=pcm16,
            sample_rate=utter_sr,
            channels=1,
            start_time=utter_t0,
            duration=max(0.0, utter_t1 - utter_t0),
        )
        speech_frames = 0
        utter_pcm_parts = []
        return out

    for chunk in chunks:
        if vad is None:
            vad = WebRtcVad(
                sr=chunk.sample_rate,
                frame_ms=cfg.frame_ms,
                aggressiveness=cfg.vad_aggressiveness,
            )
            utter_sr = chunk.sample_rate

        frame_bytes = vad.frame_bytes * chunk.channels
        frame_time = chunk.start_time

        for frame in _iter_vad_frames(chunk, frame_bytes):
            is_speech = vad.is_speech(frame, channels=chunk.channels)

            if is_speech:
                if not in_utt:
                    in_utt = True
                    utter_t0 = frame_time
                    utter_pcm_parts = []
                    speech_frames = 0
                    silence_run = 0
                speech_frames += 1
                silence_run = 0
                utter_pcm_parts.append(_to_mono_pcm16(frame, chunk.channels))
                utter_t1 = frame_time + frame_dur
            elif in_utt:
                silence_run += 1
                utter_pcm_parts.append(_to_mono_pcm16(frame, chunk.channels))
                utter_t1 = frame_time + frame_dur
                if silence_run >= end_silence_frames:
                    out = maybe_emit()
                    if out is not None:
                        yield out
            frame_time += frame_dur

    out = maybe_emit()
    if out is not None:
        yield out
