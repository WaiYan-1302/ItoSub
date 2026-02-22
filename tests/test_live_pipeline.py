from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from itosub.live.pipeline import LiveMicTranslatePipeline
from itosub.asr.stream_base import StreamTranscriber
from itosub.contracts import AudioChunk, ASRSegment, TranslationRequest


# --- fakes ---

@dataclass(frozen=True)
class FakeASRSegment:
    start: float
    end: float
    text: str


class FakeTranscriber(StreamTranscriber):
    def __init__(self, mapping):
        self.mapping = mapping  # start_time -> list[FakeASRSegment]

    def transcribe_chunk(self, chunk: AudioChunk) -> List[ASRSegment]:
        segs = self.mapping.get(chunk.start_time, [])
        # Convert to the project's ASRSegment type if needed.
        out = []
        for s in segs:
            try:
                out.append(ASRSegment(start=s.start, end=s.end, text=s.text))  # type: ignore
            except TypeError:
                # If ASRSegment has extra fields in your project, adjust here.
                out.append(ASRSegment(text=s.text))  # type: ignore
        return out


class FakeSegmenter:
    def __init__(self):
        self.buf = ""

    def ingest(self, seg: ASRSegment) -> List[str]:
        text = getattr(seg, "text", "")
        if not text:
            return []
        if self.buf:
            self.buf += " "
        self.buf += text

        committed = []
        if any(self.buf.endswith(p) for p in (".", "?", "!")):
            committed.append(self.buf.strip())
            self.buf = ""
        return committed

    def flush(self) -> List[str]:
        if self.buf.strip():
            out = [self.buf.strip()]
            self.buf = ""
            return out
        return []


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
    )

    pipeline.run()

    assert outputs == [("Hello world.", "JA(Hello world.)")]