# itosub/nlp/segmenter.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

_END_PUNCT = re.compile(r"[.!?。！？]$")

@dataclass
class Line:
    text: str
    t0: float
    t1: float

class SubtitleSegmenter:
    """
    Commit rules (semantic-first):
      1) Commit when sentence ends (punctuation).
      2) Commit when there's a big time gap (pause).
      3) Emergency commit if the buffer becomes too long (hard_max_chars).
    """
    def __init__(self, gap_sec: float = 0.8, hard_max_chars: int = 160):
        self.gap_sec = gap_sec
        self.hard_max_chars = hard_max_chars
        self._buf: List[str] = []
        self._t0: Optional[float] = None
        self._t1: Optional[float] = None
        self._last_end: Optional[float] = None

    def push(self, text: str, t0: float, t1: float) -> List[Line]:
        out: List[Line] = []
        text = (text or "").strip()
        if not text:
            return out

        # Pause boundary -> flush previous line
        if self._last_end is not None and (t0 - self._last_end) > self.gap_sec:
            out.extend(self.flush())

        if self._t0 is None:
            self._t0 = t0
        self._t1 = t1
        self._last_end = t1

        self._buf.append(text)
        merged = " ".join(self._buf).strip()

        # Commit on sentence end
        if _END_PUNCT.search(merged):
            out.append(Line(text=merged, t0=self._t0, t1=self._t1))
            self._reset()
            return out

        # Emergency commit only (prevents extremely long run-ons)
        if len(merged) >= self.hard_max_chars:
            out.append(Line(text=merged, t0=self._t0, t1=self._t1))
            self._reset()
            return out

        return out

    def flush(self) -> List[Line]:
        if not self._buf or self._t0 is None or self._t1 is None:
            self._reset()
            return []
        merged = " ".join(self._buf).strip()
        line = Line(text=merged, t0=self._t0, t1=self._t1)
        self._reset()
        return [line]

    def _reset(self) -> None:
        self._buf = []
        self._t0 = None
        self._t1 = None
        self._last_end = None