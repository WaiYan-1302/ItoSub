from __future__ import annotations

from typing import Any

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    _PYQT_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as e:  # pragma: no cover - import guard path
    QtCore = None  # type: ignore[assignment]
    QtGui = None  # type: ignore[assignment]
    QtWidgets = None  # type: ignore[assignment]
    _PYQT_IMPORT_ERROR = e


if QtWidgets is not None:
    class SettingsDialog(QtWidgets.QDialog):
        PROFILE_KEYS = (
            "sr",
            "channels",
            "rms_th",
            "model",
            "language_lock",
            "chunk_sec",
            "silence_chunks",
            "min_utter_sec",
            "translator",
            "async_translate",
            "gap_sec",
            "hard_max_chars",
            "poll_ms",
            "max_updates_per_tick",
        )
        BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
            "Balanced (Recommended)": {
                "sr": 48000,
                "channels": 1,
                "rms_th": 180.0,
                "model": "base",
                "language_lock": "auto",
                "chunk_sec": 0.5,
                "silence_chunks": 1,
                "min_utter_sec": 0.7,
                "translator": "argos",
                "async_translate": True,
                "gap_sec": 0.8,
                "hard_max_chars": 120,
                "poll_ms": 30,
                "max_updates_per_tick": 50,
            },
            "Fast Response": {
                "sr": 16000,
                "channels": 1,
                "rms_th": 180.0,
                "model": "tiny",
                "language_lock": "en",
                "chunk_sec": 0.4,
                "silence_chunks": 1,
                "min_utter_sec": 0.3,
                "translator": "argos",
                "async_translate": True,
                "gap_sec": 0.7,
                "hard_max_chars": 100,
                "poll_ms": 25,
                "max_updates_per_tick": 60,
            },
            "High Accuracy": {
                "sr": 48000,
                "channels": 1,
                "rms_th": 180.0,
                "model": "small",
                "language_lock": "auto",
                "chunk_sec": 0.6,
                "silence_chunks": 2,
                "min_utter_sec": 0.8,
                "translator": "argos",
                "async_translate": True,
                "gap_sec": 1.0,
                "hard_max_chars": 160,
                "poll_ms": 30,
                "max_updates_per_tick": 50,
            },
            "Noisy Room": {
                "sr": 48000,
                "channels": 1,
                "rms_th": 260.0,
                "model": "base",
                "language_lock": "auto",
                "chunk_sec": 0.5,
                "silence_chunks": 2,
                "min_utter_sec": 0.8,
                "translator": "argos",
                "async_translate": True,
                "gap_sec": 0.9,
                "hard_max_chars": 130,
                "poll_ms": 30,
                "max_updates_per_tick": 50,
            },
            "Rapid Turns": {
                "sr": 48000,
                "channels": 1,
                "rms_th": 170.0,
                "model": "base",
                "language_lock": "auto",
                "chunk_sec": 0.4,
                "silence_chunks": 1,
                "min_utter_sec": 0.25,
                "translator": "argos",
                "async_translate": True,
                "gap_sec": 0.7,
                "hard_max_chars": 100,
                "poll_ms": 25,
                "max_updates_per_tick": 60,
            },
        }

        def __init__(self, values: dict[str, Any], parent: QtWidgets.QWidget | None = None) -> None:
            super().__init__(parent)
            self._values = dict(values)
            self._ui_language = str(self._values.get("ui_language", "en")).lower()
            self._custom_presets: dict[str, dict[str, Any]] = {}

            self.setWindowTitle(self._t("ItoSub Settings"))
            self.resize(780, 520)

            self.sidebar = QtWidgets.QListWidget(self)
            self.sidebar.addItems(
                [
                    self._t("Audio"),
                    self._t("Speech Recognition"),
                    self._t("Translation"),
                    self._t("Overlay"),
                    self._t("Hotkeys"),
                    self._t("Advanced"),
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

            self.btn_defaults = QtWidgets.QPushButton(self._t("Restore Defaults"), self)
            self.btn_cancel = QtWidgets.QPushButton(self._t("Cancel"), self)
            self.btn_save = QtWidgets.QPushButton(self._t("Save"), self)
            self.btn_save.setDefault(True)

            self.btn_cancel.clicked.connect(self.reject)
            self.btn_save.clicked.connect(self.accept)
            self.btn_defaults.clicked.connect(self._restore_defaults)

            preset_row = QtWidgets.QHBoxLayout()
            preset_label = QtWidgets.QLabel(self._t("Profile"), self)
            self.preset_combo = QtWidgets.QComboBox(self)
            self.btn_apply_preset = QtWidgets.QPushButton(self._t("Apply"), self)
            self.btn_save_preset = QtWidgets.QPushButton(self._t("Save Current as Preset"), self)
            self.btn_apply_preset.clicked.connect(self._on_apply_preset)
            self.btn_save_preset.clicked.connect(self._on_save_preset)
            preset_row.addWidget(preset_label)
            preset_row.addWidget(self.preset_combo, stretch=1)
            preset_row.addWidget(self.btn_apply_preset)
            preset_row.addWidget(self.btn_save_preset)

            body = QtWidgets.QHBoxLayout()
            body.addWidget(self.sidebar)
            body.addWidget(self.pages, stretch=1)

            footer = QtWidgets.QHBoxLayout()
            footer.addWidget(self.btn_defaults)
            footer.addStretch(1)
            footer.addWidget(self.btn_cancel)
            footer.addWidget(self.btn_save)

            root = QtWidgets.QVBoxLayout(self)
            root.addLayout(preset_row)
            root.addLayout(body, stretch=1)
            root.addLayout(footer)

            self._populate(self._values)

        def _t(self, text: str) -> str:
            if self._ui_language != "ja":
                return text
            table = {
                "ItoSub Settings": "ItoSub 設定",
                "Audio": "音声",
                "Speech Recognition": "音声認識",
                "Translation": "翻訳",
                "Overlay": "字幕表示",
                "Hotkeys": "ショートカットキー",
                "Advanced": "詳細",
                "Restore Defaults": "初期値に戻す",
                "Cancel": "キャンセル",
                "Save": "保存",
                "Refresh": "更新",
                "Input Device": "入力デバイス",
                "Sample Rate": "サンプリング周波数",
                "Channels": "チャンネル",
                "Sensitivity (RMS)": "感度 (RMS)",
                "Model": "モデル",
                "Language Lock": "言語固定",
                "Chunk Seconds": "チャンク秒数",
                "Silence Chunks": "無音チャンク数",
                "Min Utterance Sec": "最小発話秒数",
                "Auto Detect": "自動判別",
                "English Only": "英語のみ",
                "Translator": "翻訳エンジン",
                "Async translate (EN first)": "非同期翻訳 (英語を先に表示)",
                "Print EN/JA to console": "EN/JA をコンソール出力",
                "Join Gap Sec": "結合ギャップ秒",
                "Hard Max Chars": "最大文字数 (強制確定)",
                "Show English line": "英語行を表示",
                "Max Lines": "最大行数",
                "JA Font Size": "日本語フォントサイズ",
                "EN Font Size": "英語フォントサイズ",
                "Padding": "余白",
                "Text selectable by default": "初期状態でテキスト選択を有効",
                "Background Opacity": "背景の不透明度",
                "Position Preset": "表示位置プリセット",
                "Bottom Center": "下中央",
                "Bottom Left": "左下",
                "Top Center": "上中央",
                "Keep Dragged Position": "ドラッグ位置を保持",
                "Live Preview": "ライブプレビュー",
                "Toggle EN": "英語表示切替",
                "Font Size +": "文字サイズ +",
                "Font Size -": "文字サイズ -",
                "Pause/Resume": "一時停止/再開",
                "Quit": "終了",
                "Toggle Text Selectable": "テキスト選択切替",
                "UI Language": "UI 言語",
                "UI Poll (ms)": "UI 更新間隔 (ms)",
                "Queue Max Size": "キュー最大数",
                "Max Updates/Tick": "1回更新あたり最大件数",
                "Debug VAD decisions": "VAD 判定をデバッグ表示",
                "System default input": "システム既定の入力",
                "sounddevice unavailable": "sounddevice を利用できません",
                "EN: this is a subtitle preview": "EN: subtitle preview",
                "JA: subtitle line preview": "JA: 字幕プレビュー",
                "Position preset": "表示位置",
                "Profile": "プロファイル",
                "Apply": "適用",
                "Save Current as Preset": "現在設定をプリセット保存",
                "Save Preset": "プリセット保存",
                "Preset Name": "プリセット名",
                "Preset name already exists. Overwrite?": "同名プリセットがあります。上書きしますか？",
                "Preset name cannot be empty.": "プリセット名は必須です。",
                "Balanced (Recommended)": "バランス (推奨)",
                "Fast Response": "高速応答",
                "High Accuracy": "高精度",
                "Noisy Room": "騒音環境",
                "Rapid Turns": "短い会話ターン",
            }
            return table.get(text, text)

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
            header = QtWidgets.QLabel(f"<b>{self._t(title)}</b>", page)
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
            self.device_combo = QtWidgets.QComboBox(self)
            self.device_refresh_btn = QtWidgets.QPushButton(self._t("Refresh"), self)
            self.device_refresh_btn.clicked.connect(self._refresh_device_list)
            device_row = QtWidgets.QHBoxLayout()
            device_row.addWidget(self.device_combo, stretch=1)
            device_row.addWidget(self.device_refresh_btn)
            device_wrap = QtWidgets.QWidget(self)
            device_wrap.setLayout(device_row)
            self.sr_combo = QtWidgets.QComboBox(self)
            self.sr_combo.addItems(["16000", "48000"])
            self.channels_spin = QtWidgets.QSpinBox(self)
            self.channels_spin.setRange(1, 2)
            self.rms_spin = QtWidgets.QDoubleSpinBox(self)
            self.rms_spin.setRange(1.0, 5000.0)
            self.rms_spin.setDecimals(1)
            self.rms_spin.setSingleStep(10.0)
            form.addRow(self._t("Input Device"), device_wrap)
            form.addRow(self._t("Sample Rate"), self.sr_combo)
            form.addRow(self._t("Channels"), self.channels_spin)
            form.addRow(self._t("Sensitivity (RMS)"), self.rms_spin)

        def _build_asr_page(self) -> None:
            form = self._build_page_with_form("Speech Recognition")
            self.model_combo = QtWidgets.QComboBox(self)
            self.model_combo.addItems(["tiny", "base", "small"])
            self.language_lock_combo = QtWidgets.QComboBox(self)
            self.language_lock_combo.addItem(self._t("Auto Detect"), "auto")
            self.language_lock_combo.addItem(self._t("English Only"), "en")
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
            form.addRow(self._t("Model"), self.model_combo)
            form.addRow(self._t("Language Lock"), self.language_lock_combo)
            form.addRow(self._t("Chunk Seconds"), self.chunk_sec_spin)
            form.addRow(self._t("Silence Chunks"), self.silence_chunks_spin)
            form.addRow(self._t("Min Utterance Sec"), self.min_utter_spin)

        def _build_translation_page(self) -> None:
            form = self._build_page_with_form("Translation")
            self.translator_combo = QtWidgets.QComboBox(self)
            self.translator_combo.addItems(["argos"])
            self.async_translate_check = QtWidgets.QCheckBox(self._t("Async translate (EN first)"), self)
            self.print_console_check = QtWidgets.QCheckBox(self._t("Print EN/JA to console"), self)
            self.gap_sec_spin = QtWidgets.QDoubleSpinBox(self)
            self.gap_sec_spin.setRange(0.0, 3.0)
            self.gap_sec_spin.setDecimals(2)
            self.gap_sec_spin.setSingleStep(0.1)
            self.hard_max_chars_spin = QtWidgets.QSpinBox(self)
            self.hard_max_chars_spin.setRange(20, 400)
            form.addRow(self._t("Translator"), self.translator_combo)
            form.addRow("", self.async_translate_check)
            form.addRow("", self.print_console_check)
            form.addRow(self._t("Join Gap Sec"), self.gap_sec_spin)
            form.addRow(self._t("Hard Max Chars"), self.hard_max_chars_spin)

        def _build_overlay_page(self) -> None:
            page = QtWidgets.QWidget(self)
            outer = QtWidgets.QVBoxLayout(page)
            header = QtWidgets.QLabel(f"<b>{self._t('Overlay')}</b>", page)
            outer.addWidget(header)
            form = QtWidgets.QFormLayout()
            form.setLabelAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            self.show_en_check = QtWidgets.QCheckBox(self._t("Show English line"), self)
            self.max_lines_spin = QtWidgets.QSpinBox(self)
            self.max_lines_spin.setRange(1, 8)
            self.font_size_ja_spin = QtWidgets.QSpinBox(self)
            self.font_size_ja_spin.setRange(14, 72)
            self.font_size_en_spin = QtWidgets.QSpinBox(self)
            self.font_size_en_spin.setRange(10, 48)
            self.padding_spin = QtWidgets.QSpinBox(self)
            self.padding_spin.setRange(0, 48)
            self.text_selectable_check = QtWidgets.QCheckBox(self._t("Text selectable by default"), self)
            self.overlay_opacity_spin = QtWidgets.QSpinBox(self)
            self.overlay_opacity_spin.setRange(0, 100)
            self.position_combo = QtWidgets.QComboBox(self)
            self.position_combo.addItem(self._t("Bottom Center"), "bottom_center")
            self.position_combo.addItem(self._t("Bottom Left"), "bottom_left")
            self.position_combo.addItem(self._t("Top Center"), "top_center")
            self.position_combo.addItem(self._t("Keep Dragged Position"), "custom")
            form.addRow("", self.show_en_check)
            form.addRow(self._t("Max Lines"), self.max_lines_spin)
            form.addRow(self._t("JA Font Size"), self.font_size_ja_spin)
            form.addRow(self._t("EN Font Size"), self.font_size_en_spin)
            form.addRow(self._t("Padding"), self.padding_spin)
            form.addRow("", self.text_selectable_check)
            form.addRow(self._t("Background Opacity"), self.overlay_opacity_spin)
            form.addRow(self._t("Position Preset"), self.position_combo)
            outer.addLayout(form)

            self.preview_frame = QtWidgets.QFrame(page)
            self.preview_frame.setStyleSheet(
                """
                QFrame {
                    background: #151a1f;
                    border: 1px solid #2d3742;
                    border-radius: 12px;
                }
                """
            )
            preview_layout = QtWidgets.QVBoxLayout(self.preview_frame)
            preview_layout.setContentsMargins(10, 10, 10, 10)
            preview_layout.setSpacing(6)
            preview_title = QtWidgets.QLabel(self._t("Live Preview"), self.preview_frame)
            preview_title.setStyleSheet("font-weight: 600; color: #c8d1d9;")
            self.preview_position_label = QtWidgets.QLabel("", self.preview_frame)
            self.preview_position_label.setStyleSheet("color: #8fa1b3; font-size: 11px;")

            self.preview_overlay = QtWidgets.QFrame(self.preview_frame)
            overlay_layout = QtWidgets.QVBoxLayout(self.preview_overlay)
            overlay_layout.setContentsMargins(12, 12, 12, 12)
            overlay_layout.setSpacing(4)
            self.preview_en_label = QtWidgets.QLabel(self._t("EN: this is a subtitle preview"), self.preview_overlay)
            self.preview_ja_label = QtWidgets.QLabel(self._t("JA: subtitle line preview"), self.preview_overlay)
            self.preview_en_label.setWordWrap(True)
            self.preview_ja_label.setWordWrap(True)
            overlay_layout.addWidget(self.preview_en_label)
            overlay_layout.addWidget(self.preview_ja_label)

            preview_layout.addWidget(preview_title)
            preview_layout.addWidget(self.preview_position_label)
            preview_layout.addWidget(self.preview_overlay)
            outer.addWidget(self.preview_frame)
            outer.addStretch(1)
            self.pages.addWidget(page)

            self.show_en_check.toggled.connect(self._update_overlay_preview)
            self.max_lines_spin.valueChanged.connect(self._update_overlay_preview)
            self.font_size_ja_spin.valueChanged.connect(self._update_overlay_preview)
            self.font_size_en_spin.valueChanged.connect(self._update_overlay_preview)
            self.padding_spin.valueChanged.connect(self._update_overlay_preview)
            self.overlay_opacity_spin.valueChanged.connect(self._update_overlay_preview)
            self.position_combo.currentIndexChanged.connect(self._update_overlay_preview)

        def _build_hotkeys_page(self) -> None:
            form = self._build_page_with_form("Hotkeys")
            self.hotkey_toggle_en_edit = QtWidgets.QKeySequenceEdit(self)
            self.hotkey_font_inc_edit = QtWidgets.QKeySequenceEdit(self)
            self.hotkey_font_dec_edit = QtWidgets.QKeySequenceEdit(self)
            self.hotkey_pause_edit = QtWidgets.QKeySequenceEdit(self)
            self.hotkey_quit_edit = QtWidgets.QKeySequenceEdit(self)
            self.hotkey_toggle_selectable_edit = QtWidgets.QKeySequenceEdit(self)
            form.addRow(self._t("Toggle EN"), self.hotkey_toggle_en_edit)
            form.addRow(self._t("Font Size +"), self.hotkey_font_inc_edit)
            form.addRow(self._t("Font Size -"), self.hotkey_font_dec_edit)
            form.addRow(self._t("Pause/Resume"), self.hotkey_pause_edit)
            form.addRow(self._t("Quit"), self.hotkey_quit_edit)
            form.addRow(self._t("Toggle Text Selectable"), self.hotkey_toggle_selectable_edit)

        def _build_advanced_page(self) -> None:
            form = self._build_page_with_form("Advanced")
            self.ui_language_combo = QtWidgets.QComboBox(self)
            self.ui_language_combo.addItem("English", "en")
            self.ui_language_combo.addItem("日本語", "ja")
            self.poll_ms_spin = QtWidgets.QSpinBox(self)
            self.poll_ms_spin.setRange(10, 1000)
            self.queue_maxsize_spin = QtWidgets.QSpinBox(self)
            self.queue_maxsize_spin.setRange(10, 2000)
            self.max_updates_spin = QtWidgets.QSpinBox(self)
            self.max_updates_spin.setRange(1, 500)
            self.debug_check = QtWidgets.QCheckBox(self._t("Debug VAD decisions"), self)
            form.addRow(self._t("UI Language"), self.ui_language_combo)
            form.addRow(self._t("UI Poll (ms)"), self.poll_ms_spin)
            form.addRow(self._t("Queue Max Size"), self.queue_maxsize_spin)
            form.addRow(self._t("Max Updates/Tick"), self.max_updates_spin)
            form.addRow("", self.debug_check)

        def _populate(self, values: dict[str, Any]) -> None:
            raw_custom = values.get("custom_presets", {})
            if isinstance(raw_custom, dict):
                self._custom_presets = {
                    str(name): dict(preset)
                    for name, preset in raw_custom.items()
                    if isinstance(name, str) and isinstance(preset, dict)
                }
            else:
                self._custom_presets = {}
            self._refresh_preset_combo(selected=str(values.get("active_preset", "Balanced (Recommended)")))

            device = values.get("device")
            self._refresh_device_list(selected_device=device)
            self.sr_combo.setCurrentText(str(values.get("sr", 16000)))
            self.channels_spin.setValue(self._as_int("channels", 1))
            self.rms_spin.setValue(self._as_float("rms_th", 180.0))

            self.model_combo.setCurrentText(str(values.get("model", "base")))
            self._set_combo_data(self.language_lock_combo, str(values.get("language_lock", "auto")))
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
            self.text_selectable_check.setChecked(self._as_bool("overlay_text_selectable", False))
            self.overlay_opacity_spin.setValue(self._as_int("overlay_opacity", 66))
            self._set_combo_data(self.position_combo, str(values.get("overlay_position", "bottom_center")))
            self._set_hotkey_edit(self.hotkey_toggle_en_edit, str(values.get("hotkey_toggle_en", "H")))
            self._set_hotkey_edit(self.hotkey_font_inc_edit, str(values.get("hotkey_font_inc", "+")))
            self._set_hotkey_edit(self.hotkey_font_dec_edit, str(values.get("hotkey_font_dec", "-")))
            self._set_hotkey_edit(self.hotkey_pause_edit, str(values.get("hotkey_pause", "P")))
            self._set_hotkey_edit(self.hotkey_quit_edit, str(values.get("hotkey_quit", "Esc")))
            self._set_hotkey_edit(
                self.hotkey_toggle_selectable_edit,
                str(values.get("hotkey_toggle_selectable", "T")),
            )

            self.poll_ms_spin.setValue(self._as_int("poll_ms", 60))
            self._set_combo_data(self.ui_language_combo, str(values.get("ui_language", "en")))
            self.queue_maxsize_spin.setValue(self._as_int("queue_maxsize", 100))
            self.max_updates_spin.setValue(self._as_int("max_updates_per_tick", 20))
            self.debug_check.setChecked(self._as_bool("debug", False))
            self._update_overlay_preview()

        def _restore_defaults(self) -> None:
            from itosub.app.config import load_default_config

            self._populate(load_default_config())

        def _set_combo_data(self, combo: QtWidgets.QComboBox, data: Any) -> None:
            for i in range(combo.count()):
                if combo.itemData(i) == data:
                    combo.setCurrentIndex(i)
                    return

        def _set_hotkey_edit(self, widget: QtWidgets.QKeySequenceEdit, value: str) -> None:
            widget.setKeySequence(QtGui.QKeySequence(value or ""))

        @staticmethod
        def _hotkey_text(widget: QtWidgets.QKeySequenceEdit, fallback: str) -> str:
            text = widget.keySequence().toString(QtGui.QKeySequence.SequenceFormat.PortableText).strip()
            return text or fallback

        def _refresh_device_list(self, selected_device: Any | None = None) -> None:
            current = selected_device
            if current is None and self.device_combo.count() > 0:
                current = self.device_combo.currentData()
            self.device_combo.clear()
            self.device_combo.addItem(self._t("System default input"), None)
            try:
                import sounddevice as sd

                devices = sd.query_devices()
            except Exception:
                self.device_combo.addItem(self._t("sounddevice unavailable"), None)
                self.device_combo.setEnabled(False)
                self.device_refresh_btn.setEnabled(False)
                return
            self.device_combo.setEnabled(True)
            self.device_refresh_btn.setEnabled(True)
            for idx, dev in enumerate(devices):
                max_in = int(dev.get("max_input_channels", 0))
                if max_in <= 0:
                    continue
                name = str(dev.get("name", f"Device {idx}"))
                hostapi = dev.get("hostapi")
                suffix = f" (hostapi {hostapi})" if hostapi is not None else ""
                self.device_combo.addItem(f"[{idx}] {name}{suffix}", idx)
            self._set_combo_data(self.device_combo, current)

        def _refresh_preset_combo(self, selected: str | None = None) -> None:
            self.preset_combo.clear()
            for name in self.BUILTIN_PRESETS.keys():
                self.preset_combo.addItem(self._t(name), f"builtin::{name}")
            for name in sorted(self._custom_presets.keys()):
                self.preset_combo.addItem(name, f"custom::{name}")
            if selected:
                for i in range(self.preset_combo.count()):
                    data = str(self.preset_combo.itemData(i) or "")
                    if data.endswith(f"::{selected}"):
                        self.preset_combo.setCurrentIndex(i)
                        break

        def _resolve_selected_preset(self) -> dict[str, Any] | None:
            data = str(self.preset_combo.currentData() or "")
            if data.startswith("builtin::"):
                name = data.split("::", 1)[1]
                return dict(self.BUILTIN_PRESETS.get(name, {}))
            if data.startswith("custom::"):
                name = data.split("::", 1)[1]
                return dict(self._custom_presets.get(name, {}))
            return None

        def _on_apply_preset(self) -> None:
            preset = self._resolve_selected_preset()
            if not preset:
                return
            merged = dict(self.result_values())
            merged.update(preset)
            self._populate(merged)

        def _on_save_preset(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(
                self,
                self._t("Save Preset"),
                self._t("Preset Name"),
            )
            if not ok:
                return
            preset_name = str(name or "").strip()
            if not preset_name:
                QtWidgets.QMessageBox.warning(self, self._t("Save Preset"), self._t("Preset name cannot be empty."))
                return
            if preset_name in self._custom_presets:
                ans = QtWidgets.QMessageBox.question(
                    self,
                    self._t("Save Preset"),
                    self._t("Preset name already exists. Overwrite?"),
                )
                if ans != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
            current = self.result_values()
            self._custom_presets[preset_name] = {k: current.get(k) for k in self.PROFILE_KEYS}
            self._refresh_preset_combo(selected=preset_name)

        def _update_overlay_preview(self) -> None:
            alpha = max(0.0, min(1.0, float(self.overlay_opacity_spin.value()) / 100.0))
            show_en = bool(self.show_en_check.isChecked())
            max_lines = int(self.max_lines_spin.value())
            padding = int(self.padding_spin.value())
            en_size = int(self.font_size_en_spin.value())
            ja_size = int(self.font_size_ja_spin.value())
            pos_label = self.position_combo.currentText()

            preview_alpha = int(255 * alpha)
            self.preview_overlay.setStyleSheet(
                f"""
                QFrame {{
                    background: rgba(0, 0, 0, {preview_alpha});
                    border-radius: 10px;
                    border: 1px solid rgba(255, 255, 255, 28);
                }}
                """
            )
            layout = self.preview_overlay.layout()
            if layout is not None:
                layout.setContentsMargins(padding, padding, padding, padding)

            self.preview_en_label.setVisible(show_en)
            self.preview_en_label.setStyleSheet(f"color: rgba(235, 242, 248, 220); font-size: {en_size}px;")
            self.preview_en_label.setText(self._t("EN: this is a subtitle preview"))
            self.preview_ja_label.setStyleSheet(f"color: rgba(255, 255, 255, 255); font-size: {ja_size}px;")
            if self._ui_language == "ja":
                self.preview_ja_label.setText(f"JA: 字幕プレビュー ({max_lines} 行表示)")
            else:
                self.preview_ja_label.setText(f"JA: subtitle line preview ({max_lines} lines visible)")
            self.preview_position_label.setText(f"{self._t('Position preset')}: {pos_label}")

        def result_values(self) -> dict[str, Any]:
            device = self.device_combo.currentData()
            selected_data = str(self.preset_combo.currentData() or "")
            active_preset = selected_data.split("::", 1)[1] if "::" in selected_data else "Balanced (Recommended)"
            return {
                "device": device,
                "sr": int(self.sr_combo.currentText()),
                "channels": int(self.channels_spin.value()),
                "rms_th": float(self.rms_spin.value()),
                "model": str(self.model_combo.currentText()),
                "language_lock": str(self.language_lock_combo.currentData() or "auto"),
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
                "overlay_text_selectable": bool(self.text_selectable_check.isChecked()),
                "hotkey_toggle_en": self._hotkey_text(self.hotkey_toggle_en_edit, "H"),
                "hotkey_font_inc": self._hotkey_text(self.hotkey_font_inc_edit, "+"),
                "hotkey_font_dec": self._hotkey_text(self.hotkey_font_dec_edit, "-"),
                "hotkey_pause": self._hotkey_text(self.hotkey_pause_edit, "P"),
                "hotkey_quit": self._hotkey_text(self.hotkey_quit_edit, "Esc"),
                "hotkey_toggle_selectable": self._hotkey_text(self.hotkey_toggle_selectable_edit, "T"),
                "overlay_opacity": int(self.overlay_opacity_spin.value()),
                "overlay_position": str(self.position_combo.currentData() or "bottom_center"),
                "ui_language": str(self.ui_language_combo.currentData() or "en"),
                "poll_ms": int(self.poll_ms_spin.value()),
                "queue_maxsize": int(self.queue_maxsize_spin.value()),
                "max_updates_per_tick": int(self.max_updates_spin.value()),
                "debug": bool(self.debug_check.isChecked()),
                "active_preset": active_preset,
                "custom_presets": dict(self._custom_presets),
            }
else:
    class SettingsDialog:
        def __init__(self, values: dict[str, Any], parent: Any = None) -> None:
            del values, parent
            raise ModuleNotFoundError(
                "PyQt6 is required for SettingsDialog. Install with: python -m pip install PyQt6"
            ) from _PYQT_IMPORT_ERROR
