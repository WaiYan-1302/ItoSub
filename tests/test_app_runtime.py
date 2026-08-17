from __future__ import annotations

from itosub.app.runtime import _drain_subtitle_bus, _iter_committed_lines, _subtitle_line
from itosub.nlp.segmenter import SubtitleSegmenter
from itosub.ui.bridge import SubtitleBus
from itosub.ui.overlay_qt import SubtitleLine


class _FakeOverlay:
    def __init__(self) -> None:
        self.lines: list[SubtitleLine] = []

    def add_line(self, line: SubtitleLine) -> None:
        self.lines.append(line)


def test_runtime_drain_subtitle_bus_max_items() -> None:
    bus = SubtitleBus(maxsize=10)
    overlay = _FakeOverlay()
    for i in range(4):
        bus.push(SubtitleLine(en=f"line-{i}", ja=""))
    drained = _drain_subtitle_bus(bus, overlay, max_items=3)
    assert drained == 3
    assert [ln.en for ln in overlay.lines] == ["line-0", "line-1", "line-2"]


def test_iter_committed_lines_emits_segmented_sentence() -> None:
    seg = SubtitleSegmenter(gap_sec=0.8, hard_max_chars=120)
    first = list(_iter_committed_lines(seg, 1.0, 1.3, "hello there"))
    assert first == []
    second = list(_iter_committed_lines(seg, 1.4, 1.8, "friend."))
    assert second == [(1.0, 1.8, "hello there friend.")]


def test_iter_committed_lines_accepts_short_japanese_phrase() -> None:
    seg = SubtitleSegmenter(gap_sec=0.8, hard_max_chars=120)
    lines = list(_iter_committed_lines(seg, 1.0, 1.3, "はい。", source_lang="ja"))
    assert lines == [(1.0, 1.3, "はい。")]


def test_subtitle_line_maps_japanese_source_to_japanese_field() -> None:
    line = _subtitle_line("こんにちは", "Hello", "ja", t0=1.0, t1=2.0)
    assert line.ja == "こんにちは"
    assert line.en == "Hello"
