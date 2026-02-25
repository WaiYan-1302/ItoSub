# itosub/live/pipeline.py
from __future__ import annotations

from dataclasses import fields
from typing import Callable, Iterable, Protocol

from itosub.asr.stream_base import StreamTranscriber
from itosub.contracts import AudioChunk, TranslationRequest


class Segmenter(Protocol):
    def push(self, text: str, t0: float, t1: float):
        ...

    def flush(self):
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
    def __init__(
        self,
        *,
        chunk_iter: Iterable[AudioChunk],
        transcriber: StreamTranscriber,
        segmenter: Segmenter,
        translator: Translator,
        on_commit: Callable[[float, str, str], None],  # (t1, en, ja)
        flush_on_chunk_end: bool = True,              # <-- add
        debug: bool = False,                          # <-- optional
    ) -> None:
        self.chunk_iter = chunk_iter
        self.transcriber = transcriber
        self.segmenter = segmenter
        self.translator = translator
        self.on_commit = on_commit
        self.flush_on_chunk_end = flush_on_chunk_end
        self.debug = debug

    def _emit_line(self, t1: float, en: str) -> None:
        req = _make_translation_request(en)
        res = self.translator.translate(req)

        ja = (
                getattr(res, "translated_text", None)
                or getattr(res, "text", None)
                or str(res)
        )

        self.on_commit(t1, en, ja)

    def run(self) -> None:
        for i, chunk in enumerate(self.chunk_iter, start=1):
            asr_segments = self.transcriber.transcribe_chunk(chunk)

            if self.debug:
                joined = " ".join((getattr(s, "text", "") or "").strip() for s in asr_segments).strip()
                print(f"[debug] chunk#{i} asr_segments={len(asr_segments)} text='{joined}'")

            for seg in asr_segments:
                text = (getattr(seg, "text", "") or "").strip()
                if not text:
                    continue

                t0 = float(getattr(seg, "t0", getattr(seg, "start", chunk.start_time)))
                t1 = float(getattr(seg, "t1", getattr(seg, "end", chunk.start_time + chunk.duration)))

                committed = self.segmenter.push(text=text, t0=t0, t1=t1)
                for line in committed:
                    self._emit_line(float(line.t1), line.text)

            # Milestone 4 behavior: treat chunk as final
            if self.flush_on_chunk_end:
                for line in self.segmenter.flush():
                    self._emit_line(float(line.t1), line.text)