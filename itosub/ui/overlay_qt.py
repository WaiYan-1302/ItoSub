from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Deque, List, Optional

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    _PYQT_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as e:  # pragma: no cover - import guard path
    QtCore = None  # type: ignore[assignment]
    QtGui = None  # type: ignore[assignment]
    QtWidgets = None  # type: ignore[assignment]
    _PYQT_IMPORT_ERROR = e


@dataclass(frozen=True)
class SubtitleLine:
    en: str
    ja: str
    t0: float | None = None
    t1: float | None = None


@dataclass
class OverlayConfig:
    show_en: bool = True
    max_lines: int = 4
    font_size_ja: int = 28
    font_size_en: int = 16
    padding_px: int = 14


def render_lines_to_html(lines: List[SubtitleLine], cfg: OverlayConfig) -> str:
    # newest last (bottom)
    parts: List[str] = []
    for ln in lines[-cfg.max_lines:]:
        en = (ln.en or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ja = (ln.ja or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if cfg.show_en and en:
            parts.append(
                f"<div style='font-size:{cfg.font_size_en}px; opacity:0.85; margin-bottom:2px;'>{en}</div>"
            )
        if ja:
            parts.append(
                f"<div style='font-size:{cfg.font_size_ja}px; font-weight:600;'>{ja}</div>"
            )
        parts.append("<div style='height:10px;'></div>")
    return "".join(parts).strip()


if QtWidgets is not None:
    class SubtitleOverlay(QtWidgets.QWidget):
        """
        Always-on-top subtitle overlay. Transparent window + rounded semi-opaque panel.

        Hotkeys:
          - H : toggle EN line
          - + / - : font size up/down
          - P : pause/unpause updates
          - ESC : quit
          - Drag with mouse to move
        """

        def __init__(self, cfg: OverlayConfig | None = None):
            super().__init__()
            self.cfg = cfg or OverlayConfig()
            self._paused = False
            self._lines: Deque[SubtitleLine] = deque(maxlen=50)

            self.setWindowFlags(
                QtCore.Qt.WindowType.FramelessWindowHint
                | QtCore.Qt.WindowType.WindowStaysOnTopHint
                | QtCore.Qt.WindowType.Tool
            )
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

            # Main panel (rounded)
            self.panel = QtWidgets.QFrame(self)
            self.panel.setStyleSheet(
                """
                QFrame {
                    background-color: rgba(0, 0, 0, 170);
                    border-radius: 16px;
                }
                """
            )

            self.label = QtWidgets.QTextBrowser(self.panel)
            self.label.setReadOnly(True)
            self.label.setOpenExternalLinks(False)
            self.label.setStyleSheet(
                """
                QTextBrowser {
                    background: transparent;
                    border: none;
                    color: white;
                }
                """
            )
            self.label.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.label.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            layout = QtWidgets.QVBoxLayout(self.panel)
            layout.setContentsMargins(
                self.cfg.padding_px, self.cfg.padding_px, self.cfg.padding_px, self.cfg.padding_px
            )
            layout.addWidget(self.label)

            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.addWidget(self.panel)

            self.resize(900, 220)
            self.move(80, 740)  # reasonable default on 1080p

            self._drag_pos: Optional[QtCore.QPoint] = None
            self._refresh()

        def set_paused(self, paused: bool) -> None:
            self._paused = paused

        def add_line(self, line: SubtitleLine) -> None:
            if self._paused:
                return
            self._lines.append(line)
            self._refresh()

        def set_lines(self, lines: List[SubtitleLine]) -> None:
            if self._paused:
                return
            self._lines.clear()
            for ln in lines:
                self._lines.append(ln)
            self._refresh()

        def _refresh(self) -> None:
            html = render_lines_to_html(list(self._lines), self.cfg)
            self.label.setHtml(html)

        # ----- Drag to move -----
        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            if ev.button() == QtCore.Qt.MouseButton.LeftButton:
                self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            super().mousePressEvent(ev)

        def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
            if self._drag_pos is not None and (ev.buttons() & QtCore.Qt.MouseButton.LeftButton):
                self.move(ev.globalPosition().toPoint() - self._drag_pos)
            super().mouseMoveEvent(ev)

        def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
            self._drag_pos = None
            super().mouseReleaseEvent(ev)

        # ----- Hotkeys -----
        def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
            key = ev.key()

            if key == QtCore.Qt.Key.Key_Escape:
                QtWidgets.QApplication.quit()
                return

            if key == QtCore.Qt.Key.Key_H:
                self.cfg.show_en = not self.cfg.show_en
                self._refresh()
                return

            if key in (QtCore.Qt.Key.Key_Equal, QtCore.Qt.Key.Key_Plus):
                self.cfg.font_size_ja += 2
                self.cfg.font_size_en += 1
                self._refresh()
                return

            if key in (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore):
                self.cfg.font_size_ja = max(14, self.cfg.font_size_ja - 2)
                self.cfg.font_size_en = max(10, self.cfg.font_size_en - 1)
                self._refresh()
                return

            if key == QtCore.Qt.Key.Key_P:
                self._paused = not self._paused
                return

            super().keyPressEvent(ev)
else:
    class SubtitleOverlay:
        def __init__(self, cfg: OverlayConfig | None = None) -> None:
            del cfg
            raise ModuleNotFoundError(
                "PyQt6 is required for SubtitleOverlay. Install with: python -m pip install PyQt6"
            ) from _PYQT_IMPORT_ERROR
