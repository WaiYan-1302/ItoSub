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
    text_selectable: bool = False
    hotkey_toggle_en: str = "H"
    hotkey_font_inc: str = "+"
    hotkey_font_dec: str = "-"
    hotkey_pause: str = "P"
    hotkey_quit: str = "Esc"
    hotkey_toggle_selectable: str = "T"
    bg_opacity: int = 66
    position_preset: str = "bottom_center"


def merge_subtitle_line(
    lines: List[SubtitleLine],
    new_line: SubtitleLine,
    *,
    max_lines: int,
) -> List[SubtitleLine]:
    out = list(lines)
    # Drop exact duplicates.
    for prev in reversed(out):
        if (
            prev.en == new_line.en
            and prev.ja == new_line.ja
            and prev.t0 == new_line.t0
            and prev.t1 == new_line.t1
        ):
            return out[-max(1, int(max_lines)):]

    # Async EN-first then JA-later path: replace pending line instead of appending.
    if new_line.ja:
        for i in range(len(out) - 1, -1, -1):
            prev = out[i]
            same_en = (prev.en or "").strip() == (new_line.en or "").strip()
            pending_ja = not (prev.ja or "").strip()
            same_time = (prev.t0 == new_line.t0 and prev.t1 == new_line.t1)
            if same_en and pending_ja and same_time:
                out[i] = new_line
                return out[-max(1, int(max_lines)):]

    out.append(new_line)
    return out[-max(1, int(max_lines)):]


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
        escape_requested = QtCore.pyqtSignal()
        """
        Always-on-top subtitle overlay. Transparent window + rounded semi-opaque panel.

        Hotkeys:
          - H : toggle EN line
          - + / - : font size up/down
          - P : pause/unpause updates
          - ESC : return to main window
          - Drag with mouse to move
        """

        def __init__(self, cfg: OverlayConfig | None = None):
            super().__init__()
            self.cfg = cfg or OverlayConfig()
            self._paused = False
            self._lines: Deque[SubtitleLine] = deque(maxlen=max(1, int(self.cfg.max_lines)))

            self.setWindowFlags(
                QtCore.Qt.WindowType.FramelessWindowHint
                | QtCore.Qt.WindowType.WindowStaysOnTopHint
                | QtCore.Qt.WindowType.Tool
            )
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

            # Main panel (rounded)
            self.panel = QtWidgets.QFrame(self)
            self._apply_panel_style()

            self.label = QtWidgets.QTextBrowser(self.panel)
            self.label.setReadOnly(True)
            self.label.setOpenExternalLinks(False)
            self._apply_text_interaction()
            self.label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
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
            layout.setSpacing(6)
            self.loading_wrap = QtWidgets.QFrame(self.panel)
            self.loading_wrap.setStyleSheet(
                """
                QFrame {
                    background: rgba(255, 255, 255, 20);
                    border-radius: 8px;
                }
                """
            )
            loading_layout = QtWidgets.QVBoxLayout(self.loading_wrap)
            loading_layout.setContentsMargins(10, 8, 10, 8)
            loading_layout.setSpacing(6)
            self.loading_label = QtWidgets.QLabel("Preparing speech recognition...", self.loading_wrap)
            self.loading_label.setStyleSheet("color: rgba(240, 248, 255, 220); font-size: 13px;")
            self.loading_bar = QtWidgets.QProgressBar(self.loading_wrap)
            self.loading_bar.setRange(0, 0)
            self.loading_bar.setTextVisible(False)
            self.loading_bar.setFixedHeight(10)
            self.loading_bar.setStyleSheet(
                """
                QProgressBar {
                    background: rgba(255, 255, 255, 18);
                    border: 1px solid rgba(255, 255, 255, 25);
                    border-radius: 5px;
                }
                QProgressBar::chunk {
                    background: rgba(167, 232, 255, 220);
                    border-radius: 5px;
                }
                """
            )
            loading_layout.addWidget(self.loading_label)
            loading_layout.addWidget(self.loading_bar)
            self.loading_wrap.hide()
            layout.addWidget(self.loading_wrap)
            layout.addWidget(self.label)
            grip_row = QtWidgets.QHBoxLayout()
            grip_row.addStretch(1)
            self.size_grip = QtWidgets.QSizeGrip(self.panel)
            self.size_grip.setFixedSize(16, 16)
            self.size_grip.setStyleSheet("background: transparent;")
            grip_row.addWidget(self.size_grip, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
            layout.addLayout(grip_row)

            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.addWidget(self.panel)

            self.resize(900, 220)
            self.apply_position_preset()

            self._drag_pos: Optional[QtCore.QPoint] = None
            self.panel.installEventFilter(self)
            self.label.viewport().installEventFilter(self)
            self._refresh()

        def set_paused(self, paused: bool) -> None:
            self._paused = paused

        def add_line(self, line: SubtitleLine) -> None:
            if self._paused:
                return
            merged = merge_subtitle_line(list(self._lines), line, max_lines=max(1, int(self.cfg.max_lines)))
            self._lines = deque(merged, maxlen=max(1, int(self.cfg.max_lines)))
            self._refresh()

        def set_lines(self, lines: List[SubtitleLine]) -> None:
            if self._paused:
                return
            self._trim_history()
            self._lines.clear()
            for ln in lines[-max(1, int(self.cfg.max_lines)):]:
                self._lines.append(ln)
            self._refresh()

        def _refresh(self) -> None:
            self._trim_history()
            html = render_lines_to_html(list(self._lines), self.cfg)
            self.label.setHtml(html)
            # Always keep latest subtitle visible even if user scrolled up previously.
            bar = self.label.verticalScrollBar()
            bar.setValue(bar.maximum())

        def _trim_history(self) -> None:
            keep = max(1, int(self.cfg.max_lines))
            if self._lines.maxlen != keep:
                self._lines = deque(self._lines, maxlen=keep)

        def set_loading(self, loading: bool, message: str = "Preparing speech recognition...") -> None:
            if loading:
                self.loading_label.setText(str(message or "Preparing speech recognition..."))
                self.loading_wrap.show()
            else:
                self.loading_wrap.hide()

        def _apply_text_interaction(self) -> None:
            if bool(self.cfg.text_selectable):
                self.label.setTextInteractionFlags(
                    QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
                    | QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
                )
            else:
                self.label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        def eventFilter(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> bool:
            if obj in (self.panel, self.label.viewport()):
                if ev.type() == QtCore.QEvent.Type.MouseButtonPress:
                    me = ev
                    if isinstance(me, QtGui.QMouseEvent) and me.button() == QtCore.Qt.MouseButton.LeftButton:
                        self._drag_pos = me.globalPosition().toPoint() - self.frameGeometry().topLeft()
                        return True
                if ev.type() == QtCore.QEvent.Type.MouseMove:
                    me = ev
                    if isinstance(me, QtGui.QMouseEvent):
                        if self._drag_pos is not None and (me.buttons() & QtCore.Qt.MouseButton.LeftButton):
                            self.move(me.globalPosition().toPoint() - self._drag_pos)
                            return True
                if ev.type() == QtCore.QEvent.Type.MouseButtonRelease:
                    me = ev
                    if isinstance(me, QtGui.QMouseEvent) and me.button() == QtCore.Qt.MouseButton.LeftButton:
                        self._drag_pos = None
                        return True
            return super().eventFilter(obj, ev)

        def _apply_panel_style(self) -> None:
            alpha = max(0, min(255, int(round((self.cfg.bg_opacity / 100.0) * 255.0))))
            self.panel.setStyleSheet(
                f"""
                QFrame {{
                    background-color: rgba(0, 0, 0, {alpha});
                    border-radius: 16px;
                }}
                """
            )

        def apply_position_preset(self) -> None:
            preset = str(self.cfg.position_preset or "bottom_center").lower()
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen is None:
                return
            geom = screen.availableGeometry()
            margin = 40
            x = geom.left() + max(0, (geom.width() - self.width()) // 2)
            y = geom.top() + max(0, geom.height() - self.height() - margin)
            if preset == "bottom_left":
                x = geom.left() + margin
            elif preset == "top_center":
                y = geom.top() + margin
            elif preset == "custom":
                return
            self.move(x, y)

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
            if self._matches_hotkey(ev, self.cfg.hotkey_quit):
                self.escape_requested.emit()
                return

            if self._matches_hotkey(ev, self.cfg.hotkey_toggle_en):
                self.cfg.show_en = not self.cfg.show_en
                self._refresh()
                return

            if self._matches_hotkey(ev, self.cfg.hotkey_font_inc):
                self.cfg.font_size_ja += 2
                self.cfg.font_size_en += 1
                self._refresh()
                return

            if self._matches_hotkey(ev, self.cfg.hotkey_font_dec):
                self.cfg.font_size_ja = max(14, self.cfg.font_size_ja - 2)
                self.cfg.font_size_en = max(10, self.cfg.font_size_en - 1)
                self._refresh()
                return

            if self._matches_hotkey(ev, self.cfg.hotkey_pause):
                self._paused = not self._paused
                return

            if self._matches_hotkey(ev, self.cfg.hotkey_toggle_selectable):
                self.cfg.text_selectable = not self.cfg.text_selectable
                self._apply_text_interaction()
                return

            super().keyPressEvent(ev)

        def _matches_hotkey(self, ev: QtGui.QKeyEvent, binding: str) -> bool:
            target = self._normalize_hotkey(binding)
            if not target:
                return False
            seq = QtGui.QKeySequence(ev.keyCombination())
            current = seq.toString(QtGui.QKeySequence.SequenceFormat.PortableText)
            if not current:
                current = seq.toString(QtGui.QKeySequence.SequenceFormat.NativeText)
            current_norm = self._normalize_hotkey(current)
            return current_norm == target

        @staticmethod
        def _normalize_hotkey(value: str) -> str:
            raw = str(value or "").strip()
            if not raw:
                return ""
            key = QtGui.QKeySequence(raw).toString(QtGui.QKeySequence.SequenceFormat.PortableText).strip()
            if not key:
                key = raw
            kl = key.lower()
            if kl in ("escape",):
                return "esc"
            if kl in ("plus", "equal"):
                return "+"
            if kl in ("minus", "underscore"):
                return "-"
            return kl
else:
    class SubtitleOverlay:
        def __init__(self, cfg: OverlayConfig | None = None) -> None:
            del cfg
            raise ModuleNotFoundError(
                "PyQt6 is required for SubtitleOverlay. Install with: python -m pip install PyQt6"
            ) from _PYQT_IMPORT_ERROR
