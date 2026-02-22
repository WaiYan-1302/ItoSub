from __future__ import annotations

from dataclasses import fields
from typing import Callable, Iterable, List, Optional, Protocol

from itosub.contracts import ASRSegment, TranslationRequest
from itosub.asr.stream_base import StreamTranscriber
from itosub.contracts import AudioChunk


class Segmenter(Protocol):
    def ingest(self, seg: ASRSegment) -> List[str]:
        """Feed one ASR segment; return 0+ committed EN subtitle lines."""
        ...

    def flush(self) -> List[str]:
        """Force-commit remaining buffered text; return 0+ lines."""
        ...


class Translator(Protocol):
    def translate(self, req: TranslationRequest):
        ...


def _make_translation_request(text: str) -> TranslationRequest:
    names = {f.name for f in fields(TranslationRequest)}
    kwargs = {}
    if "text" in names:
        kwargs["text"] = text
    if "source_lang" in names:
        kwargs["source_lang"] = "en"
    if "target_lang" in names:
        kwargs["target_lang"] = "ja"
    return TranslationRequest(**kwargs)  # type: ignore[arg-type]


class LiveMicTranslatePipeline:
    """
    Orchestrates: mic -> chunk -> ASR -> segmenter -> translator -> callback
    """

    def __init__(
        self,
        *,
        chunk_iter: Iterable[AudioChunk],
        transcriber: StreamTranscriber,
        segmenter: Segmenter,
        translator: Translator,
        on_commit: Callable[[float, str, str], None],
    ) -> None:
        self.chunk_iter = chunk_iter
        self.transcriber = transcriber
        self.segmenter = segmenter
        self.translator = translator
        self.on_commit = on_commit

    def run(self) -> None:
        for chunk in self.chunk_iter:
            asr_segments = self.transcriber.transcribe_chunk(chunk)
            for seg in asr_segments:
                committed_lines = self.segmenter.ingest(seg)
                for line_en in committed_lines:
                    req = _make_translation_request(line_en)
                    res = self.translator.translate(req)
                    # TranslationResult likely has `.text`; fall back to str(res)
                    line_ja = getattr(res, "text", None) or str(res)
                    self.on_commit(getattr(seg, "end", chunk.start_time + chunk.duration), line_en, line_ja)

        for line_en in self.segmenter.flush():
            req = _make_translation_request(line_en)
            res = self.translator.translate(req)
            line_ja = getattr(res, "text", None) or str(res)
            self.on_commit(-1.0, line_en, line_ja)