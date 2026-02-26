from itosub.demos.demo_live_overlay_translate import (
    _dedupe_repeated_words,
    _drain_subtitle_bus,
    _is_low_value_fragment,
    _iter_committed_lines,
)
from itosub.nlp.segmenter import SubtitleSegmenter
from itosub.ui.bridge import SubtitleBus
from itosub.ui.overlay_qt import SubtitleLine


class _FakeOverlay:
    def __init__(self) -> None:
        self.lines: list[SubtitleLine] = []

    def add_line(self, line: SubtitleLine) -> None:
        self.lines.append(line)


def test_subtitle_bus_drops_oldest_when_full() -> None:
    bus = SubtitleBus(maxsize=2)
    bus.push(SubtitleLine(en="one", ja="1"))
    bus.push(SubtitleLine(en="two", ja="2"))
    bus.push(SubtitleLine(en="three", ja="3"))

    first = bus.pop()
    second = bus.pop()
    assert first is not None and first.en == "two"
    assert second is not None and second.en == "three"
    assert bus.pop() is None


def test_drain_subtitle_bus_respects_max_items() -> None:
    bus = SubtitleBus(maxsize=10)
    overlay = _FakeOverlay()
    for i in range(3):
        bus.push(SubtitleLine(en=f"line-{i}", ja=f"ja-{i}"))

    drained = _drain_subtitle_bus(bus, overlay, max_items=2)
    assert drained == 2
    assert [ln.en for ln in overlay.lines] == ["line-0", "line-1"]


def test_overlay_text_filters_match_milestone5_behavior() -> None:
    assert _dedupe_repeated_words("go go go now", max_repeat=2) == "go go now"
    assert _is_low_value_fragment("uh")
    assert not _is_low_value_fragment("hello world")


def test_iter_committed_lines_uses_segmenter_boundaries() -> None:
    segmenter = SubtitleSegmenter(gap_sec=0.8, hard_max_chars=120)
    first = list(_iter_committed_lines(segmenter, 1.0, 1.2, "Hello there"))
    assert first == []

    second = list(_iter_committed_lines(segmenter, 1.3, 1.6, "world."))
    assert len(second) == 1
    t0, t1, text = second[0]
    assert (t0, t1, text) == (1.0, 1.6, "Hello there world.")
