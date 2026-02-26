from __future__ import annotations

from typing import Any

try:
    from PyQt6 import QtCore, QtWidgets

    _PYQT_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as e:  # pragma: no cover - import guard path
    QtCore = None  # type: ignore[assignment]
    QtWidgets = None  # type: ignore[assignment]
    _PYQT_IMPORT_ERROR = e


if QtWidgets is not None:
    class SettingsDialog(QtWidgets.QDialog):
        def __init__(self, values: dict[str, Any], parent: QtWidgets.QWidget | None = None) -> None:
            super().__init__(parent)
            self.setWindowTitle("ItoSub Settings")
            self.resize(780, 520)
            self._values = dict(values)

            self.sidebar = QtWidgets.QListWidget(self)
            self.sidebar.addItems(
                [
                    "Audio",
                    "ASR",
                    "Translation",
                    "Overlay",
                    "Hotkeys",
                    "Advanced",
                ]
            )
            self.sidebar.setMaximumWidth(170)

            self.pages = QtWidgets.QStackedWidget(self)
            self._build_audio_page()
            self._build_asr_page()
            self._build_translation_page()
            self._build_overlay_page()
            self._build_hotkeys_page()
            self._build_advanced_page()
            self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
            self.sidebar.setCurrentRow(0)

            self.btn_defaults = QtWidgets.QPushButton("Restore Defaults", self)
            self.btn_cancel = QtWidgets.QPushButton("Cancel", self)
            self.btn_save = QtWidgets.QPushButton("Save", self)
            self.btn_save.setDefault(True)

            self.btn_cancel.clicked.connect(self.reject)
            self.btn_save.clicked.connect(self.accept)
            self.btn_defaults.clicked.connect(self._restore_defaults)

            body = QtWidgets.QHBoxLayout()
            body.addWidget(self.sidebar)
            body.addWidget(self.pages, stretch=1)

            footer = QtWidgets.QHBoxLayout()
            footer.addWidget(self.btn_defaults)
            footer.addStretch(1)
            footer.addWidget(self.btn_cancel)
            footer.addWidget(self.btn_save)

            root = QtWidgets.QVBoxLayout(self)
            root.addLayout(body, stretch=1)
            root.addLayout(footer)

            self._populate(self._values)

        def _as_int(self, key: str, default: int) -> int:
            try:
                return int(self._values.get(key, default))
            except (TypeError, ValueError):
                return default

        def _as_float(self, key: str, default: float) -> float:
            try:
                return float(self._values.get(key, default))
            except (TypeError, ValueError):
                return default

        def _as_bool(self, key: str, default: bool) -> bool:
            raw = self._values.get(key, default)
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                return raw.strip().lower() in ("1", "true", "yes", "on")
            return bool(raw)

        def _build_page_with_form(self, title: str) -> QtWidgets.QFormLayout:
            page = QtWidgets.QWidget(self)
            outer = QtWidgets.QVBoxLayout(page)
            header = QtWidgets.QLabel(f"<b>{title}</b>", page)
            outer.addWidget(header)
            form = QtWidgets.QFormLayout()
            form.setLabelAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            outer.addLayout(form)
            outer.addStretch(1)
            self.pages.addWidget(page)
            return form

        def _build_audio_page(self) -> None:
            form = self._build_page_with_form("Audio")
            self.device_edit = QtWidgets.QLineEdit(self)
            self.device_edit.setPlaceholderText("blank = default input device")
            self.sr_combo = QtWidgets.QComboBox(self)
            self.sr_combo.addItems(["16000", "48000"])
            self.channels_spin = QtWidgets.QSpinBox(self)
            self.channels_spin.setRange(1, 2)
            self.rms_spin = QtWidgets.QDoubleSpinBox(self)
            self.rms_spin.setRange(1.0, 5000.0)
            self.rms_spin.setDecimals(1)
            self.rms_spin.setSingleStep(10.0)
            form.addRow("Device ID", self.device_edit)
            form.addRow("Sample Rate", self.sr_combo)
            form.addRow("Channels", self.channels_spin)
            form.addRow("Sensitivity (RMS)", self.rms_spin)

        def _build_asr_page(self) -> None:
            form = self._build_page_with_form("ASR")
            self.model_combo = QtWidgets.QComboBox(self)
            self.model_combo.addItems(["tiny", "base", "small"])
            self.chunk_sec_spin = QtWidgets.QDoubleSpinBox(self)
            self.chunk_sec_spin.setRange(0.1, 2.0)
            self.chunk_sec_spin.setDecimals(2)
            self.chunk_sec_spin.setSingleStep(0.05)
            self.silence_chunks_spin = QtWidgets.QSpinBox(self)
            self.silence_chunks_spin.setRange(1, 20)
            self.min_utter_spin = QtWidgets.QDoubleSpinBox(self)
            self.min_utter_spin.setRange(0.1, 5.0)
            self.min_utter_spin.setDecimals(2)
            self.min_utter_spin.setSingleStep(0.1)
            form.addRow("Model", self.model_combo)
            form.addRow("Chunk Seconds", self.chunk_sec_spin)
            form.addRow("Silence Chunks", self.silence_chunks_spin)
            form.addRow("Min Utterance Sec", self.min_utter_spin)

        def _build_translation_page(self) -> None:
            form = self._build_page_with_form("Translation")
            self.translator_combo = QtWidgets.QComboBox(self)
            self.translator_combo.addItems(["stub", "argos"])
            self.async_translate_check = QtWidgets.QCheckBox("Async translate (EN first)", self)
            self.print_console_check = QtWidgets.QCheckBox("Print EN/JA to console", self)
            self.gap_sec_spin = QtWidgets.QDoubleSpinBox(self)
            self.gap_sec_spin.setRange(0.0, 3.0)
            self.gap_sec_spin.setDecimals(2)
            self.gap_sec_spin.setSingleStep(0.1)
            self.hard_max_chars_spin = QtWidgets.QSpinBox(self)
            self.hard_max_chars_spin.setRange(20, 400)
            form.addRow("Translator", self.translator_combo)
            form.addRow("", self.async_translate_check)
            form.addRow("", self.print_console_check)
            form.addRow("Join Gap Sec", self.gap_sec_spin)
            form.addRow("Hard Max Chars", self.hard_max_chars_spin)

        def _build_overlay_page(self) -> None:
            form = self._build_page_with_form("Overlay")
            self.show_en_check = QtWidgets.QCheckBox("Show English line", self)
            self.max_lines_spin = QtWidgets.QSpinBox(self)
            self.max_lines_spin.setRange(1, 8)
            self.font_size_ja_spin = QtWidgets.QSpinBox(self)
            self.font_size_ja_spin.setRange(14, 72)
            self.font_size_en_spin = QtWidgets.QSpinBox(self)
            self.font_size_en_spin.setRange(10, 48)
            self.padding_spin = QtWidgets.QSpinBox(self)
            self.padding_spin.setRange(0, 48)
            form.addRow("", self.show_en_check)
            form.addRow("Max Lines", self.max_lines_spin)
            form.addRow("JA Font Size", self.font_size_ja_spin)
            form.addRow("EN Font Size", self.font_size_en_spin)
            form.addRow("Padding", self.padding_spin)

        def _build_hotkeys_page(self) -> None:
            page = QtWidgets.QWidget(self)
            layout = QtWidgets.QVBoxLayout(page)
            layout.addWidget(QtWidgets.QLabel("<b>Hotkeys</b>", page))
            layout.addWidget(
                QtWidgets.QLabel(
                    "Overlay hotkeys are fixed in v1:\nH toggle EN, +/- font, P pause, ESC quit.",
                    page,
                )
            )
            layout.addStretch(1)
            self.pages.addWidget(page)

        def _build_advanced_page(self) -> None:
            form = self._build_page_with_form("Advanced")
            self.poll_ms_spin = QtWidgets.QSpinBox(self)
            self.poll_ms_spin.setRange(10, 1000)
            self.queue_maxsize_spin = QtWidgets.QSpinBox(self)
            self.queue_maxsize_spin.setRange(10, 2000)
            self.max_updates_spin = QtWidgets.QSpinBox(self)
            self.max_updates_spin.setRange(1, 500)
            self.debug_check = QtWidgets.QCheckBox("Debug VAD decisions", self)
            form.addRow("UI Poll (ms)", self.poll_ms_spin)
            form.addRow("Queue Max Size", self.queue_maxsize_spin)
            form.addRow("Max Updates/Tick", self.max_updates_spin)
            form.addRow("", self.debug_check)

        def _populate(self, values: dict[str, Any]) -> None:
            device = values.get("device")
            self.device_edit.setText("" if device is None else str(device))
            self.sr_combo.setCurrentText(str(values.get("sr", 16000)))
            self.channels_spin.setValue(self._as_int("channels", 1))
            self.rms_spin.setValue(self._as_float("rms_th", 180.0))

            self.model_combo.setCurrentText(str(values.get("model", "base")))
            self.chunk_sec_spin.setValue(self._as_float("chunk_sec", 0.5))
            self.silence_chunks_spin.setValue(self._as_int("silence_chunks", 2))
            self.min_utter_spin.setValue(self._as_float("min_utter_sec", 0.6))

            self.translator_combo.setCurrentText(str(values.get("translator", "stub")))
            self.async_translate_check.setChecked(self._as_bool("async_translate", True))
            self.print_console_check.setChecked(self._as_bool("print_console", True))
            self.gap_sec_spin.setValue(self._as_float("gap_sec", 0.9))
            self.hard_max_chars_spin.setValue(self._as_int("hard_max_chars", 140))

            self.show_en_check.setChecked(self._as_bool("show_en", True))
            self.max_lines_spin.setValue(self._as_int("max_lines", 4))
            self.font_size_ja_spin.setValue(self._as_int("font_size_ja", 28))
            self.font_size_en_spin.setValue(self._as_int("font_size_en", 16))
            self.padding_spin.setValue(self._as_int("padding_px", 14))

            self.poll_ms_spin.setValue(self._as_int("poll_ms", 60))
            self.queue_maxsize_spin.setValue(self._as_int("queue_maxsize", 100))
            self.max_updates_spin.setValue(self._as_int("max_updates_per_tick", 20))
            self.debug_check.setChecked(self._as_bool("debug", False))

        def _restore_defaults(self) -> None:
            from itosub.app.config import load_default_config

            self._populate(load_default_config())

        def result_values(self) -> dict[str, Any]:
            device_raw = self.device_edit.text().strip()
            device = None if device_raw == "" else int(device_raw)
            return {
                "device": device,
                "sr": int(self.sr_combo.currentText()),
                "channels": int(self.channels_spin.value()),
                "rms_th": float(self.rms_spin.value()),
                "model": str(self.model_combo.currentText()),
                "chunk_sec": float(self.chunk_sec_spin.value()),
                "silence_chunks": int(self.silence_chunks_spin.value()),
                "min_utter_sec": float(self.min_utter_spin.value()),
                "translator": str(self.translator_combo.currentText()),
                "async_translate": bool(self.async_translate_check.isChecked()),
                "print_console": bool(self.print_console_check.isChecked()),
                "gap_sec": float(self.gap_sec_spin.value()),
                "hard_max_chars": int(self.hard_max_chars_spin.value()),
                "show_en": bool(self.show_en_check.isChecked()),
                "max_lines": int(self.max_lines_spin.value()),
                "font_size_ja": int(self.font_size_ja_spin.value()),
                "font_size_en": int(self.font_size_en_spin.value()),
                "padding_px": int(self.padding_spin.value()),
                "poll_ms": int(self.poll_ms_spin.value()),
                "queue_maxsize": int(self.queue_maxsize_spin.value()),
                "max_updates_per_tick": int(self.max_updates_spin.value()),
                "debug": bool(self.debug_check.isChecked()),
            }
else:
    class SettingsDialog:
        def __init__(self, values: dict[str, Any], parent: Any = None) -> None:
            del values, parent
            raise ModuleNotFoundError(
                "PyQt6 is required for SettingsDialog. Install with: python -m pip install PyQt6"
            ) from _PYQT_IMPORT_ERROR

