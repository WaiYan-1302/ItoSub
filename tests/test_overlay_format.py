from itosub.ui.overlay_qt import OverlayConfig, SubtitleLine, render_lines_to_html

def test_render_lines_to_html_contains_text():
    cfg = OverlayConfig(show_en=True)
    html = render_lines_to_html([SubtitleLine(en="Hello", ja="こんにちは")], cfg)
    assert "Hello" in html
    assert "こんにちは" in html