from __future__ import annotations

from array import array

from itosub.asr.faster_whisper_pcm16 import FasterWhisperPCM16Transcriber
from itosub.audio.vad import EnergyVAD
from itosub.contracts import ASRSegment, AudioChunk
from itosub.live.live_transcribe import LiveUtteranceTranscriber


def _pcm16_constant(amplitude: int, frames: int, channels: int = 1) -> bytes:
    return array("h", [amplitude] * (frames * channels)).tobytes()


def test_live_utterance_transcriber_finalizes_once_and_emits_asr(monkeypatch):
    sr = 16000
    channels = 1
    frames_per_chunk = int(0.5 * sr)

    silence = _pcm16_constant(0, frames_per_chunk, channels)
    speech = _pcm16_constant(3000, frames_per_chunk, channels)

    chunks = [
        AudioChunk(pcm16=silence, sample_rate=sr, channels=channels, start_time=0.0, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=0.5, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=1.0, duration=0.5),
        AudioChunk(pcm16=silence, sample_rate=sr, channels=channels, start_time=1.5, duration=0.5),
        AudioChunk(pcm16=silence, sample_rate=sr, channels=channels, start_time=2.0, duration=0.5),
    ]

    transcriber = FasterWhisperPCM16Transcriber(model_size="tiny")
    calls = []

    def fake_transcribe_utterance(
        pcm16: bytes, sample_rate: int, channels: int, utter_t0: float
    ):
        calls.append((len(pcm16), sample_rate, channels, utter_t0))
        return [ASRSegment(text="hello world", t0=utter_t0 + 0.1, t1=utter_t0 + 0.9, is_final=True)]

    monkeypatch.setattr(transcriber, "transcribe_utterance", fake_transcribe_utterance)

    outputs = []

    runner = LiveUtteranceTranscriber(
        chunk_iter=chunks,
        transcriber=transcriber,
        vad=EnergyVAD(rms_threshold=500.0),
        on_asr=lambda t0, t1, text: outputs.append((t0, t1, text)),
        silence_chunks_to_finalize=2,
        min_utter_sec=0.6,
    )
    runner.run()

    assert len(calls) == 1
    assert calls[0][1:] == (sr, channels, 0.5)
    assert outputs == [(0.6, 1.4, "hello world")]


def test_live_utterance_transcriber_force_finalizes_on_max_utter(monkeypatch):
    sr = 16000
    channels = 1
    frames_per_chunk = int(0.5 * sr)
    speech = _pcm16_constant(3000, frames_per_chunk, channels)

    chunks = [
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=0.0, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=0.5, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=1.0, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=1.5, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=2.0, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=2.5, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=3.0, duration=0.5),
        AudioChunk(pcm16=speech, sample_rate=sr, channels=channels, start_time=3.5, duration=0.5),
    ]

    transcriber = FasterWhisperPCM16Transcriber(model_size="tiny")
    calls = []

    def fake_transcribe_utterance(
        pcm16: bytes, sample_rate: int, channels: int, utter_t0: float
    ):
        calls.append((len(pcm16), sample_rate, channels, utter_t0))
        return [ASRSegment(text=f"u{utter_t0:.1f}", t0=utter_t0, t1=utter_t0 + 0.5, is_final=True)]

    monkeypatch.setattr(transcriber, "transcribe_utterance", fake_transcribe_utterance)

    outputs = []
    runner = LiveUtteranceTranscriber(
        chunk_iter=chunks,
        transcriber=transcriber,
        vad=EnergyVAD(rms_threshold=500.0),
        on_asr=lambda t0, t1, text: outputs.append((t0, t1, text)),
        silence_chunks_to_finalize=2,
        min_utter_sec=0.6,
        max_utter_sec=1.5,
    )
    runner.run()

    assert len(calls) == 3
    assert [call[3] for call in calls] == [0.0, 1.5, 3.0]
    assert [text for _, _, text in outputs] == ["u0.0", "u1.5", "u3.0"]
