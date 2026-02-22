# itosub/nlp/postprocess_en.py
from __future__ import annotations
import re

_TIME_DOT = re.compile(r"(\d{1,2})\.(\d{2})\s*([ap])\.m\.", flags=re.IGNORECASE)

def normalize_en(text: str) -> str:
    text = text.strip()

    # 1.30 a.m. -> 1:30 a.m.
    def repl(m: re.Match) -> str:
        h, mm, ap = m.group(1), m.group(2), m.group(3).lower()
        return f"{h}:{mm} {ap}.m."

    text = _TIME_DOT.sub(repl, text)
    return text