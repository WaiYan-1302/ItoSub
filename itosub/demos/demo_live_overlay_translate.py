from __future__ import annotations

from itosub.app.main import main
from itosub.app.runtime import (
    _dedupe_repeated_words,
    _drain_subtitle_bus,
    _is_low_value_fragment,
    _iter_committed_lines,
)

__all__ = [
    "main",
    "_dedupe_repeated_words",
    "_drain_subtitle_bus",
    "_is_low_value_fragment",
    "_iter_committed_lines",
]


if __name__ == "__main__":
    raise SystemExit(main())
