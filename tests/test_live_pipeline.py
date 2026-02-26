from __future__ import annotations

from dataclasses import dataclass
from typing import List

from itosub.asr.stream_base import StreamTranscriber
from itosub.contracts import ASRSegment, AudioChunk, TranslationRequest
from itosub.live.pipeline import LiveMicTranslatePipeline


@dataclass(frozen=True)
class FakeASRSegment:
    t0: float
    t1: float
    text: str


@dataclass
class FakeLine:
    text: str
    t0: float
    t1: float


class FakeTranscriber(StreamTranscriber):
    def __init__(self, mapping):
        self.mapping = mapping  # start_time -> list[FakeASRSegment]

    def transcribe_chunk(self, chunk: AudioChunk) -> List[ASRSegment]:
        segs = self.mapping.get(chunk.start_time, [])
        return [ASRSegment(text=s.text, t0=s.t0, t1=s.t1, is_final=True) for s in segs]


class FakeSegmenter:
    def __init__(self):
        self.buf: list[str] = []
        self.t0: float | None = None
        self.t1: float | None = None

    def push(self, text: str, t0: float, t1: float) -> List[FakeLine]:
        self.buf.append(text)
        if self.t0 is None:
            self.t0 = t0
        self.t1 = t1

        merged = " ".join(self.buf).strip()
        if merged.endswith("."):
            out = [FakeLine(text=merged, t0=self.t0, t1=self.t1)]
            self.buf = []
            self.t0 = None
            self.t1 = None
            return out
        return []

    def flush(self) -> List[FakeLine]:
        if not self.buf or self.t0 is None or self.t1 is None:
            self.buf = []
            self.t0 = None
            self.t1 = None
            return []
        merged = " ".join(self.buf).strip()
        out = [FakeLine(text=merged, t0=self.t0, t1=self.t1)]
        self.buf = []
        self.t0 = None
        self.t1 = None
        return out


class FakeTranslator:
    def translate(self, req: TranslationRequest):
        text = getattr(req, "text", "")
        return type("R", (), {"text": f"JA({text})"})()


def test_live_pipeline_commits_and_translates():
    chunks = [
        AudioChunk(pcm16=b"x", sample_rate=16000, channels=1, start_time=0.0, duration=1.5),
        AudioChunk(pcm16=b"y", sample_rate=16000, channels=1, start_time=1.5, duration=1.5),
    ]

    mapping = {
        0.0: [FakeASRSegment(0.0, 0.7, "Hello")],
        1.5: [FakeASRSegment(1.5, 2.1, "world.")],
    }

    transcriber = FakeTranscriber(mapping)
    segmenter = FakeSegmenter()
    translator = FakeTranslator()

    outputs = []

    def on_commit(ts, en, ja):
        outputs.append((en, ja))

    pipeline = LiveMicTranslatePipeline(
        chunk_iter=chunks,
        transcriber=transcriber,
        segmenter=segmenter,
        translator=translator,
        on_commit=on_commit,
        flush_on_chunk_end=False,
    )

    pipeline.run()

    assert outputs == [("Hello world.", "JA(Hello world.)")]
