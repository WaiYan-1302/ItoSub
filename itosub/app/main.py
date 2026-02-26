from __future__ import annotations

import math
import os
import queue
import signal
import sys
import threading
import time
import traceback
import webbrowser

from itosub.app.config import load_user_config, resolve_args, save_user_config
from itosub.app.diagnostics import hint_for_exception, summarize_exception
from itosub.app.logging_setup import setup_app_logger
from itosub.app.runtime import _drain_subtitle_bus, _preload_asr_runtime, _run_worker
from itosub.app.state import RuntimeState, RuntimeStateTracker
from itosub.audio.mic import SoundDeviceMicSource
from itosub.ui.bridge import SubtitleBus


def main(argv: list[str] | None = None) -> int:
    args = resolve_args(argv)
    logger, log_dir, log_path = setup_app_logger()
    logger.info("app_start", extra={"config_path": str(getattr(args, "config", "")), "argv": argv or []})

    if args.list_devices:
        print(SoundDeviceMicSource.list_devices())
        return 0

    # Load ASR runtime stack before PyQt initializes to avoid Windows DLL init conflicts.
    asr_runtime_ready = False
    startup_preload_error = ""
    try:
        _preload_asr_runtime()
        asr_runtime_ready = True
    except Exception:
        startup_preload_error = traceback.format_exc()
        logger.exception("asr_runtime_preload_failed_startup")

    from PyQt6 import QtCore, QtGui, QtWidgets
    from itosub.app.main_window_qt import MainWindow
    from itosub.app.settings_qt import SettingsDialog
    from itosub.ui.overlay_qt import OverlayConfig, SubtitleLine, SubtitleOverlay

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ItoSub.App")
        except Exception:
            pass

    app = QtWidgets.QApplication(sys.argv)
    if getattr(sys, "frozen", False):
        project_root = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    app_icon_path = os.path.join(project_root, "assets", "image", "ItoSubIcon.png")
    legacy_icon_path = os.path.join(os.path.dirname(__file__), "resources", "app_icon.png")
    icon_path = app_icon_path if os.path.exists(app_icon_path) else legacy_icon_path
    app_icon = QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    def _tr(en: str, ja: str) -> str:
        return ja if str(getattr(args, "ui_language", "en")).lower() == "ja" else en

    class _MicLevelMonitor:
        _display_gain = 0.4

        def __init__(self, *, device: int | None, sr: int, channels: int, rms_threshold: float) -> None:
            self._device = device
            self._sr = int(sr)
            self._channels = int(channels)
            self._rms_threshold = max(1.0, float(rms_threshold))
            self._lock = threading.Lock()
            self._stop: threading.Event | None = None
            self._thread: threading.Thread | None = None
            self._level = 0
            self._active = False

        def update_config(self, *, device: int | None, sr: int, channels: int, rms_threshold: float) -> None:
            self._device = device
            self._sr = int(sr)
            self._channels = int(channels)
            self._rms_threshold = max(1.0, float(rms_threshold))
            self.restart()

        def start(self) -> None:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._run, name="itosub-mic-level-monitor", daemon=True)
            self._thread.start()

        def stop(self) -> None:
            ev = self._stop
            if ev is not None:
                ev.set()
            thread = self._thread
            if thread is not None:
                thread.join(timeout=1.0)
            self._thread = None
            self._stop = None
            with self._lock:
                self._level = 0
                self._active = False

        def restart(self) -> None:
            self.stop()
            self.start()

        def is_active(self) -> bool:
            with self._lock:
                return self._active

        def level(self) -> int:
            with self._lock:
                return int(self._level)

        def _run(self) -> None:
            stop = self._stop
            if stop is None:
                return
            try:
                import sounddevice as sd
            except Exception:
                return
            block_size = max(256, int(self._sr * 0.05))
            try:
                with sd.RawInputStream(
                    samplerate=self._sr,
                    channels=self._channels,
                    dtype="int16",
                    device=self._device,
                    blocksize=block_size,
                ) as stream:
                    with self._lock:
                        self._active = True
                    while not stop.is_set():
                        data, _overflow = stream.read(block_size)
                        samples = memoryview(data).cast("h")
                        if len(samples) == 0:
                            rms = 0.0
                        else:
                            sum_sq = 0.0
                            for sample in samples:
                                sum_sq += float(sample) * float(sample)
                            rms = math.sqrt(sum_sq / float(len(samples)))
                        scaled = min(100.0, (rms / self._rms_threshold) * 100.0 * self._display_gain)
                        with self._lock:
                            # Smoothing keeps the meter stable and easier to read.
                            self._level = int((0.75 * self._level) + (0.25 * scaled))
            except Exception:
                with self._lock:
                    self._active = False
                    self._level = 0

    mic_monitor = _MicLevelMonitor(
        device=args.device,
        sr=int(args.sr),
        channels=int(args.channels),
        rms_threshold=float(args.rms_th),
    )
    mic_monitor.start()

    overlay = SubtitleOverlay(
        OverlayConfig(
            show_en=bool(args.show_en),
            max_lines=max(1, int(args.max_lines)),
            font_size_ja=max(10, int(args.font_size_ja)),
            font_size_en=max(8, int(args.font_size_en)),
            padding_px=max(0, int(args.padding_px)),
            text_selectable=bool(args.overlay_text_selectable),
            hotkey_toggle_en=str(args.hotkey_toggle_en),
            hotkey_font_inc=str(args.hotkey_font_inc),
            hotkey_font_dec=str(args.hotkey_font_dec),
            hotkey_pause=str(args.hotkey_pause),
            hotkey_quit=str(args.hotkey_quit),
            hotkey_toggle_selectable=str(args.hotkey_toggle_selectable),
            bg_opacity=max(0, min(100, int(args.overlay_opacity))),
            position_preset=str(args.overlay_position),
        )
    )
    overlay.hide()

    main_window = MainWindow()
    main_window.apply_ui_language(str(args.ui_language))
    main_window.set_brand_image(os.path.join(project_root, "assets", "image", "ItoSubTransparent.png"))
    if not app_icon.isNull():
        main_window.setWindowIcon(app_icon)

    err_q: "queue.Queue[tuple[int, str]]" = queue.Queue(maxsize=8)
    ready_q: "queue.Queue[int]" = queue.Queue(maxsize=8)
    bus = SubtitleBus(maxsize=max(1, int(args.queue_maxsize)))
    state = RuntimeStateTracker()

    runtime_lock = threading.Lock()
    worker_thread: threading.Thread | None = None
    stop_event: threading.Event | None = None
    worker_generation = 0
    timer: QtCore.QTimer | None = None
    loading_hide_deadline = 0.0

    def _build_status_line() -> str:
        device = "default" if args.device is None else str(args.device)
        if str(args.ui_language) == "ja":
            return (
                f"マイク: {device} | SR: {int(args.sr)} | モデル: {str(args.model)} | "
                f"言語固定: {str(args.language_lock)} | "
                f"翻訳: {str(args.translator)}"
            )
        return (
            f"Mic: {device} | SR: {int(args.sr)} | Model: {str(args.model)} | "
            f"Lang: {str(args.language_lock)} | "
            f"Translator: {str(args.translator)}"
        )

    def _apply_overlay_settings() -> None:
        overlay.cfg.show_en = bool(args.show_en)
        overlay.cfg.max_lines = max(1, int(args.max_lines))
        overlay.cfg.font_size_ja = max(10, int(args.font_size_ja))
        overlay.cfg.font_size_en = max(8, int(args.font_size_en))
        overlay.cfg.padding_px = max(0, int(args.padding_px))
        overlay.cfg.text_selectable = bool(args.overlay_text_selectable)
        overlay.cfg.hotkey_toggle_en = str(args.hotkey_toggle_en)
        overlay.cfg.hotkey_font_inc = str(args.hotkey_font_inc)
        overlay.cfg.hotkey_font_dec = str(args.hotkey_font_dec)
        overlay.cfg.hotkey_pause = str(args.hotkey_pause)
        overlay.cfg.hotkey_quit = str(args.hotkey_quit)
        overlay.cfg.hotkey_toggle_selectable = str(args.hotkey_toggle_selectable)
        overlay.cfg.bg_opacity = max(0, min(100, int(args.overlay_opacity)))
        overlay.cfg.position_preset = str(args.overlay_position)
        panel_layout = overlay.panel.layout()
        if panel_layout is not None:
            panel_layout.setContentsMargins(
                overlay.cfg.padding_px,
                overlay.cfg.padding_px,
                overlay.cfg.padding_px,
                overlay.cfg.padding_px,
            )
        overlay._apply_panel_style()  # noqa: SLF001
        overlay._apply_text_interaction()  # noqa: SLF001
        overlay.apply_position_preset()
        overlay._refresh()  # noqa: SLF001

    def _worker_entry(local_generation: int, local_stop_event: threading.Event) -> None:
        try:
            _run_worker(
                args,
                bus,
                local_stop_event,
                on_ready=lambda: ready_q.put_nowait(local_generation),
                logger=logger,
            )
        except Exception:
            err = traceback.format_exc()
            logger.exception("worker_crash", extra={"generation": local_generation})
            try:
                err_q.put_nowait((local_generation, err))
            except queue.Full:
                pass

    def _start_runtime() -> None:
        nonlocal asr_runtime_ready, worker_generation, worker_thread, stop_event, loading_hide_deadline
        with runtime_lock:
            if worker_thread is not None and worker_thread.is_alive():
                return

            if not asr_runtime_ready:
                try:
                    _preload_asr_runtime()
                    asr_runtime_ready = True
                except Exception:
                    detail = traceback.format_exc()
                    logger.exception("asr_runtime_preload_failed")
                    state.set_error(detail)
                    summary = summarize_exception(detail or startup_preload_error)
                    hint = hint_for_exception(summary)
                    QtWidgets.QMessageBox.critical(
                        main_window,
                        _tr("Speech Recognition Runtime Error", "音声認識ランタイムエラー"),
                        _tr(
                            "Failed to initialize speech recognition runtime stack (torch/ctranslate2/faster-whisper).\n",
                            "音声認識ランタイム (torch/ctranslate2/faster-whisper) の初期化に失敗しました。\n",
                        )
                        + f"{_tr('Cause', '原因')}: {summary}\n"
                        + f"{_tr('Hint', '対処')}: {hint}\n"
                        + f"{_tr('Log', 'ログ')}: {log_path}",
                    )
                    return

            state.set_starting()
            stop_event = threading.Event()
            worker_generation += 1
            generation = worker_generation
            local_stop = stop_event
            worker_thread = threading.Thread(
                target=lambda: _worker_entry(generation, local_stop),
                name="itosub-live-asr-overlay-worker",
                daemon=True,
            )
            worker_thread.start()
            overlay.set_paused(False)
            overlay.set_loading(True, message=_tr("Preparing speech recognition...", "音声認識の準備中..."))
            loading_hide_deadline = 0.0
            overlay.show()
            overlay.activateWindow()
            state.set_running()
            logger.info("runtime_started", extra={"generation": generation})

    def _stop_runtime() -> None:
        nonlocal stop_event, loading_hide_deadline
        with runtime_lock:
            if stop_event is not None:
                stop_event.set()
            overlay.set_paused(False)
            overlay.set_loading(False)
            loading_hide_deadline = 0.0
            overlay.hide()
            state.set_stopped()
            logger.info("runtime_stopped")

    def _toggle_pause() -> None:
        if state.state == RuntimeState.PAUSED:
            overlay.set_paused(False)
            state.set_resumed()
            logger.info("runtime_resumed")
            return
        if state.state == RuntimeState.RUNNING:
            overlay.set_paused(True)
            state.set_paused()
            logger.info("runtime_paused")

    tray = None
    act_show_app = None
    act_start_stop = None
    act_pause_resume = None
    act_show_hide = None
    act_settings = None
    act_open_logs = None
    act_quit = None

    def _sync_window_state() -> None:
        main_window.set_running(state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING))
        main_window.set_status_text(_build_status_line())

    def _refresh_tray_actions() -> None:
        if act_show_app is not None:
            act_show_app.setText(_tr("Show App", "アプリを表示"))
        if act_start_stop is not None:
            if state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
                act_start_stop.setText(_tr("Stop", "停止"))
            else:
                act_start_stop.setText(_tr("Start", "開始"))
        if act_pause_resume is not None:
            if state.state == RuntimeState.PAUSED:
                act_pause_resume.setText(_tr("Resume", "再開"))
                act_pause_resume.setEnabled(True)
            elif state.state == RuntimeState.RUNNING:
                act_pause_resume.setText(_tr("Pause", "一時停止"))
                act_pause_resume.setEnabled(True)
            else:
                act_pause_resume.setText(_tr("Pause", "一時停止"))
                act_pause_resume.setEnabled(False)
        if act_show_hide is not None:
            act_show_hide.setText(
                _tr("Hide Overlay", "字幕を隠す") if overlay.isVisible() else _tr("Show Overlay", "字幕を表示")
            )
        if act_settings is not None:
            act_settings.setText(_tr("Settings", "設定"))
            act_settings.setEnabled(state.state != RuntimeState.STARTING)
        if act_open_logs is not None:
            act_open_logs.setText(_tr("Open Logs", "ログを開く"))
            act_open_logs.setEnabled(True)
        if act_quit is not None:
            act_quit.setText(_tr("Quit", "終了"))

    def _start_from_ui() -> None:
        _start_runtime()
        if state.state == RuntimeState.RUNNING:
            if tray is not None:
                main_window.hide()
            _sync_window_state()
            _refresh_tray_actions()

    def _stop_from_ui() -> None:
        _stop_runtime()
        main_window.show()
        main_window.activateWindow()
        _sync_window_state()
        _refresh_tray_actions()

    def _open_settings() -> None:
        nonlocal bus
        current_values, _ = load_user_config(config_path=args.config)
        for key in current_values.keys():
            if hasattr(args, key):
                current_values[key] = getattr(args, key)

        dlg = SettingsDialog(current_values, main_window)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        try:
            updated = dlg.result_values()
        except ValueError:
            QtWidgets.QMessageBox.warning(
                main_window,
                _tr("Invalid Settings", "設定エラー"),
                _tr("Please review audio device and numeric fields.", "音声デバイスや数値項目を確認してください。"),
            )
            return

        changed_keys = {k for k, v in updated.items() if getattr(args, k, None) != v}
        if not changed_keys:
            return

        save_user_config(updated, config_path=args.config)
        logger.info(
            "settings_saved",
            extra={"changed_keys": sorted(changed_keys), "config_path": str(getattr(args, "config", ""))},
        )
        for key, value in updated.items():
            setattr(args, key, value)

        main_window.apply_ui_language(str(args.ui_language))
        mic_monitor.update_config(
            device=args.device,
            sr=int(args.sr),
            channels=int(args.channels),
            rms_threshold=float(args.rms_th),
        )
        _apply_overlay_settings()
        if timer is not None:
            timer.setInterval(max(10, int(args.poll_ms)))
        if "queue_maxsize" in changed_keys:
            bus = SubtitleBus(maxsize=max(1, int(args.queue_maxsize)))

        restart_keys = {
            "device",
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
            "print_console",
            "gap_sec",
            "hard_max_chars",
            "debug",
            "queue_maxsize",
        }
        if changed_keys.intersection(restart_keys) and state.state in (
            RuntimeState.RUNNING,
            RuntimeState.PAUSED,
            RuntimeState.STARTING,
        ):
            _stop_runtime()
            _start_runtime()

        _sync_window_state()
        _refresh_tray_actions()

    def _open_logs_folder() -> None:
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(log_dir))  # type: ignore[attr-defined]
                opened = True
            else:
                opened = webbrowser.open(str(log_dir))
            logger.info("open_logs", extra={"log_dir": str(log_dir), "opened": bool(opened)})
        except Exception:
            logger.exception("open_logs_failed", extra={"log_dir": str(log_dir)})

    _last_mic_test = 0.0
    _mic_playback_lock = threading.Lock()
    _mic_playback_state = "idle"
    _mic_record_stop_event: threading.Event | None = None
    _mic_playback_stop_event: threading.Event | None = None

    def _test_mic() -> None:
        nonlocal _last_mic_test
        if _last_mic_test > time.time():
            _last_mic_test = 0.0
            main_window.set_meter_level(0)
            return
        _last_mic_test = time.time() + 3.0
        if not mic_monitor.is_active():
            mic_monitor.restart()

    def _mic_playback_is_active() -> bool:
        with _mic_playback_lock:
            return _mic_playback_state != "idle"

    def _test_mic_playback() -> None:
        nonlocal _last_mic_test, _mic_playback_state, _mic_record_stop_event, _mic_playback_stop_event
        duration_sec = 10.0
        if not mic_monitor.is_active():
            mic_monitor.restart()

        with _mic_playback_lock:
            if _mic_playback_state == "recording":
                if _mic_record_stop_event is not None:
                    _mic_record_stop_event.set()
                _last_mic_test = 0.0
                main_window.set_meter_level(0)
                return
            if _mic_playback_state == "playback":
                if _mic_playback_stop_event is not None:
                    _mic_playback_stop_event.set()
                _last_mic_test = 0.0
                main_window.set_meter_level(0)
                return
            _mic_record_stop_event = threading.Event()
            _mic_playback_stop_event = threading.Event()
            record_stop = _mic_record_stop_event
            playback_stop = _mic_playback_stop_event
            _mic_playback_state = "recording"

        _last_mic_test = time.time() + duration_sec + 12.0

        def _run_record_playback(local_record_stop: threading.Event, local_playback_stop: threading.Event) -> None:
            nonlocal _mic_playback_state, _mic_record_stop_event, _mic_playback_stop_event, _last_mic_test
            try:
                import sounddevice as sd

                sr = int(args.sr)
                ch = int(args.channels)
                block_size = max(256, int(sr * 0.1))
                bytes_per_sample = 2
                target_frames = int(sr * duration_sec)
                recorded: list[bytes] = []
                frames_recorded = 0

                with sd.RawInputStream(
                    samplerate=sr,
                    channels=ch,
                    dtype="int16",
                    device=args.device,
                    blocksize=block_size,
                ) as istream:
                    while frames_recorded < target_frames and not local_record_stop.is_set():
                        remaining = target_frames - frames_recorded
                        frames = min(block_size, remaining)
                        data, _overflow = istream.read(frames)
                        chunk = bytes(data)
                        if chunk:
                            recorded.append(chunk)
                        frames_recorded += frames

                with _mic_playback_lock:
                    if _mic_playback_state == "recording":
                        _mic_playback_state = "playback"

                if not recorded:
                    return
                _last_mic_test = time.time() + max(1.0, float(frames_recorded) / float(max(1, sr)))

                with sd.RawOutputStream(
                    samplerate=sr,
                    channels=ch,
                    dtype="int16",
                    blocksize=block_size,
                ) as ostream:
                    for chunk in recorded:
                        if local_playback_stop.is_set():
                            break
                        expected = len(chunk) // (bytes_per_sample * ch)
                        if expected <= 0:
                            continue
                        ostream.write(chunk)
            except Exception:
                logger.exception("mic_test_playback_failed")
                QtCore.QTimer.singleShot(
                    0,
                    lambda: QtWidgets.QMessageBox.warning(
                        main_window,
                        _tr("Mic Test Playback Error", "マイク再生テストエラー"),
                        _tr(
                            "Failed to record/play back test audio. Check device selection.",
                            "録音または再生に失敗しました。デバイス設定を確認してください。",
                        ),
                    ),
                )
            finally:
                with _mic_playback_lock:
                    _mic_playback_state = "idle"
                    _mic_record_stop_event = None
                    _mic_playback_stop_event = None
                _last_mic_test = 0.0
                QtCore.QTimer.singleShot(0, lambda: main_window.set_meter_level(0))

        threading.Thread(
            target=lambda: _run_record_playback(record_stop, playback_stop),
            name="itosub-mic-playback-test",
            daemon=True,
        ).start()

    def _on_overlay_escape() -> None:
        main_window.show()
        main_window.activateWindow()
        overlay.hide()
        _refresh_tray_actions()

    if QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        icon = app_icon if not app_icon.isNull() else app.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        tray = QtWidgets.QSystemTrayIcon(icon, app)
        tray.setToolTip("ItoSub")
        menu = QtWidgets.QMenu()
        act_show_app = menu.addAction(_tr("Show App", "アプリを表示"))
        menu.addSeparator()
        act_start_stop = menu.addAction(_tr("Start", "開始"))
        act_pause_resume = menu.addAction(_tr("Pause", "一時停止"))
        act_show_hide = menu.addAction(_tr("Show Overlay", "字幕を表示"))
        act_settings = menu.addAction(_tr("Settings", "設定"))
        act_open_logs = menu.addAction(_tr("Open Logs", "ログを開く"))
        menu.addSeparator()
        act_quit = menu.addAction(_tr("Quit", "終了"))
        tray.setContextMenu(menu)

        def _on_start_stop() -> None:
            if state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
                _stop_from_ui()
            else:
                _start_from_ui()

        def _on_show_hide() -> None:
            if overlay.isVisible():
                overlay.hide()
            else:
                overlay.show()
                overlay.activateWindow()
            _refresh_tray_actions()

        def _on_show_app() -> None:
            main_window.show()
            main_window.activateWindow()

        act_show_app.triggered.connect(_on_show_app)
        act_start_stop.triggered.connect(_on_start_stop)
        act_pause_resume.triggered.connect(lambda: (_toggle_pause(), _sync_window_state(), _refresh_tray_actions()))
        act_show_hide.triggered.connect(_on_show_hide)
        act_settings.triggered.connect(_open_settings)
        act_open_logs.triggered.connect(_open_logs_folder)
        act_quit.triggered.connect(app.quit)
        tray.activated.connect(
            lambda reason: _on_show_app()
            if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        tray.show()

    main_window.run_requested.connect(_start_from_ui)
    main_window.stop_requested.connect(_stop_from_ui)
    main_window.settings_requested.connect(_open_settings)
    main_window.test_mic_requested.connect(_test_mic)
    main_window.test_mic_playback_requested.connect(_test_mic_playback)
    overlay.escape_requested.connect(_on_overlay_escape)

    timer = QtCore.QTimer()

    def _on_tick() -> None:
        nonlocal loading_hide_deadline
        drained = _drain_subtitle_bus(bus, overlay, max(1, int(args.max_updates_per_tick)))
        if drained > 0 and state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
            overlay.set_loading(False)
            loading_hide_deadline = 0.0

        while True:
            try:
                ready_generation = ready_q.get_nowait()
            except queue.Empty:
                break
            if ready_generation != worker_generation:
                continue
            if state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
                # If no speech yet, reassure user and auto-hide shortly.
                overlay.set_loading(True, message=_tr("Ready. Waiting for speech...", "準備完了。音声入力待ち..."))
                loading_hide_deadline = time.time() + 1.2

        if loading_hide_deadline > 0.0 and time.time() >= loading_hide_deadline:
            overlay.set_loading(False)
            loading_hide_deadline = 0.0

        if _last_mic_test > time.time() or _mic_playback_is_active():
            level = mic_monitor.level()
            if _last_mic_test > time.time() or _mic_playback_is_active():
                # Reduce mic-test meter sensitivity by half for clearer feedback.
                level = int(level * 0.5)
            main_window.set_meter_level(level)
        else:
            main_window.set_meter_level(0)

        if worker_thread is not None and not worker_thread.is_alive():
            if state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
                if stop_event is not None and stop_event.is_set():
                    state.set_stopped()
                else:
                    state.set_error("worker stopped unexpectedly")

        try:
            generation, err = err_q.get_nowait()
        except queue.Empty:
            _sync_window_state()
            _refresh_tray_actions()
            return

        if generation != worker_generation:
            _sync_window_state()
            _refresh_tray_actions()
            return

        print("Live overlay worker crashed:")
        print(err)
        logger.error("worker_crash_reported", extra={"generation": generation, "detail": err})
        state.set_error(err)
        summary = summarize_exception(err)
        hint = hint_for_exception(summary)
        overlay.add_line(
            SubtitleLine(
                en="Worker crashed. See console log.",
                ja="\u30ef\u30fc\u30ab\u30fc\u304c\u505c\u6b62\u3057\u307e\u3057\u305f\u3002\u30b3\u30f3\u30bd\u30fc\u30eb\u30ed\u30b0\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
            )
        )
        overlay.set_loading(False)
        loading_hide_deadline = 0.0
        QtWidgets.QMessageBox.critical(
            main_window,
            _tr("Runtime Worker Error", "ランタイムワーカーエラー"),
            f"{_tr('Cause', '原因')}: {summary}\n{_tr('Hint', '対処')}: {hint}\n{_tr('Log', 'ログ')}: {log_path}",
        )
        main_window.show()
        main_window.activateWindow()
        _sync_window_state()
        _refresh_tray_actions()

    timer.timeout.connect(_on_tick)
    timer.start(max(10, int(args.poll_ms)))

    def _on_about_to_quit() -> None:
        logger.info("app_quit")
        with _mic_playback_lock:
            if _mic_record_stop_event is not None:
                _mic_record_stop_event.set()
            if _mic_playback_stop_event is not None:
                _mic_playback_stop_event.set()
        mic_monitor.stop()
        _stop_runtime()
        if tray is not None:
            tray.hide()

    app.aboutToQuit.connect(_on_about_to_quit)
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    _sync_window_state()
    _refresh_tray_actions()
    main_window.show()

    print("ItoSub app ready. Open Settings, then press Start to run overlay.")
    print(f"Logs: {log_path}")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

