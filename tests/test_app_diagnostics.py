from __future__ import annotations

from itosub.app.diagnostics import hint_for_exception, summarize_exception


def test_summarize_exception_picks_last_meaningful_line() -> None:
    detail = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\n'
        "    boom()\n"
        "RuntimeError: failed to start worker"
    )
    assert summarize_exception(detail) == "RuntimeError: failed to start worker"


def test_summarize_exception_truncates_long_line() -> None:
    detail = "ValueError: " + ("x" * 500)
    out = summarize_exception(detail, max_len=60)
    assert out.startswith("ValueError: ")
    assert out.endswith("...")
    assert len(out) <= 60


def test_hint_for_exception_winerror_1114() -> None:
    hint = hint_for_exception("OSError: [WinError 1114] c10.dll failed")
    assert "Torch DLL init failed" in hint


def test_hint_for_exception_default() -> None:
    hint = hint_for_exception("RuntimeError: unknown")
    assert hint == "Check logs for full traceback."
