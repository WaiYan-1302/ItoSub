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
    Merge ASR segments into subtitle-friendly lines.
    Commit when:
      - sentence ends (punctuation), OR
      - time gap between segments is big, OR
      - line is too long
    """
    def __init__(self, max_chars: int = 70, gap_sec: float = 0.8):
        self.max_chars = max_chars
        self.gap_sec = gap_sec
        self._buf_text: List[str] = []
        self._t0: Optional[float] = None
        self._t1: Optional[float] = None
        self._last_end: Optional[float] = None

    def push(self, text: str, t0: float, t1: float) -> List[Line]:
        out: List[Line] = []
        text = (text or "").strip()
        if not text:
            return out

        # commit if big gap from previous segment
        if self._last_end is not None and (t0 - self._last_end) > self.gap_sec:
            out.extend(self.flush())

        if self._t0 is None:
            self._t0 = t0
        self._t1 = t1
        self._last_end = t1

        self._buf_text.append(text)
        merged = " ".join(self._buf_text).strip()

        should_commit = (
            len(merged) >= self.max_chars
            or _END_PUNCT.search(merged) is not None
        )

        if should_commit:
            out.append(Line(text=merged, t0=self._t0, t1=self._t1))
            self._reset()

        return out

    def flush(self) -> List[Line]:
        if not self._buf_text or self._t0 is None or self._t1 is None:
            self._reset()
            return []
        merged = " ".join(self._buf_text).strip()
        line = Line(text=merged, t0=self._t0, t1=self._t1)
        self._reset()
        return [line]

    def _reset(self) -> None:
        self._buf_text = []
        self._t0 = None
        self._t1 = None
        self._last_end = None