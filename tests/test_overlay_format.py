from itosub.ui.overlay_qt import OverlayConfig, SubtitleLine, merge_subtitle_line, render_lines_to_html


def test_render_lines_to_html_contains_text() -> None:
    cfg = OverlayConfig(show_en=True)
    html = render_lines_to_html([SubtitleLine(en="Hello", ja="こんにちは")], cfg)
    assert "Hello" in html
    assert "こんにちは" in html


def test_merge_subtitle_line_replaces_pending_en_with_ja() -> None:
    lines = [SubtitleLine(en="Nothing's coming up.", ja="", t0=1.0, t1=2.0)]
    new_line = SubtitleLine(en="Nothing's coming up.", ja="仮訳", t0=1.0, t1=2.0)
    merged = merge_subtitle_line(lines, new_line, max_lines=4)
    assert len(merged) == 1
    assert merged[0].ja == "仮訳"


def test_merge_subtitle_line_drops_exact_duplicate() -> None:
    line = SubtitleLine(en="A", ja="B", t0=1.0, t1=2.0)
    merged = merge_subtitle_line([line], line, max_lines=4)
    assert merged == [line]
