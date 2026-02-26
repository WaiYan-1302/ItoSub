from __future__ import annotations

import sys
from PyQt6 import QtCore, QtWidgets

from itosub.ui.overlay_qt import OverlayConfig, SubtitleLine, SubtitleOverlay


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    overlay = SubtitleOverlay(OverlayConfig(show_en=True, max_lines=4))
    overlay.show()

    demo_lines = [
        SubtitleLine(en="Hello everyone.", ja="みなさん、こんにちは。"),
        SubtitleLine(en="Today I will present my project.", ja="今日は私のプロジェクトを発表します。"),
        SubtitleLine(en="It translates English to Japanese live.", ja="英語を日本語にリアルタイム翻訳します。"),
        SubtitleLine(en="Press H to hide English.", ja="Hキーで英語を非表示にできます。"),
    ]

    i = 0

    def tick():
        nonlocal i
        overlay.add_line(demo_lines[i % len(demo_lines)])
        i += 1

    timer = QtCore.QTimer()
    timer.timeout.connect(tick)
    timer.start(1200)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())