from __future__ import annotations

import os
import queue
import random
import signal
import sys
import threading
import traceback
import webbrowser

from itosub.app.config import load_user_config, resolve_args, save_user_config
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
    try:
        _preload_asr_runtime()
        asr_runtime_ready = True
    except Exception:
        logger.exception("asr_runtime_preload_failed_startup")

    from PyQt6 import QtCore, QtWidgets
    from itosub.app.main_window_qt import MainWindow
    from itosub.app.settings_qt import SettingsDialog
    from itosub.ui.overlay_qt import OverlayConfig, SubtitleLine, SubtitleOverlay

    app = QtWidgets.QApplication(sys.argv)

    overlay = SubtitleOverlay(
        OverlayConfig(
            show_en=bool(args.show_en),
            max_lines=max(1, int(args.max_lines)),
            font_size_ja=max(10, int(args.font_size_ja)),
            font_size_en=max(8, int(args.font_size_en)),
            padding_px=max(0, int(args.padding_px)),
        )
    )
    overlay.hide()

    main_window = MainWindow()

    err_q: "queue.Queue[tuple[int, str]]" = queue.Queue(maxsize=8)
    bus = SubtitleBus(maxsize=max(1, int(args.queue_maxsize)))
    state = RuntimeStateTracker()

    runtime_lock = threading.Lock()
    worker_thread: threading.Thread | None = None
    stop_event: threading.Event | None = None
    worker_generation = 0
    timer: QtCore.QTimer | None = None

    def _build_status_line() -> str:
        device = "default" if args.device is None else str(args.device)
        return (
            f"Mic: {device} | SR: {int(args.sr)} | Model: {str(args.model)} | "
            f"Translator: {str(args.translator)}"
        )

    def _apply_overlay_settings() -> None:
        overlay.cfg.show_en = bool(args.show_en)
        overlay.cfg.max_lines = max(1, int(args.max_lines))
        overlay.cfg.font_size_ja = max(10, int(args.font_size_ja))
        overlay.cfg.font_size_en = max(8, int(args.font_size_en))
        overlay.cfg.padding_px = max(0, int(args.padding_px))
        panel_layout = overlay.panel.layout()
        if panel_layout is not None:
            panel_layout.setContentsMargins(
                overlay.cfg.padding_px,
                overlay.cfg.padding_px,
                overlay.cfg.padding_px,
                overlay.cfg.padding_px,
            )
        overlay._refresh()  # noqa: SLF001

    def _worker_entry(local_generation: int, local_stop_event: threading.Event) -> None:
        try:
            _run_worker(args, bus, local_stop_event, logger=logger)
        except Exception:
            err = traceback.format_exc()
            logger.exception("worker_crash", extra={"generation": local_generation})
            try:
                err_q.put_nowait((local_generation, err))
            except queue.Full:
                pass

    def _start_runtime() -> None:
        nonlocal asr_runtime_ready, worker_generation, worker_thread, stop_event
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
                    QtWidgets.QMessageBox.critical(
                        main_window,
                        "ASR Runtime Error",
                        "Failed to initialize ASR runtime stack (torch/ctranslate2/faster-whisper).\n"
                        f"See log: {log_path}",
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
            overlay.show()
            overlay.activateWindow()
            state.set_running()
            logger.info("runtime_started", extra={"generation": generation})

    def _stop_runtime() -> None:
        nonlocal stop_event
        with runtime_lock:
            if stop_event is not None:
                stop_event.set()
            overlay.set_paused(False)
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

    def _sync_window_state() -> None:
        main_window.set_running(state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING))
        main_window.set_status_text(_build_status_line())

    def _refresh_tray_actions() -> None:
        if act_start_stop is not None:
            if state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
                act_start_stop.setText("Stop")
            else:
                act_start_stop.setText("Start")
        if act_pause_resume is not None:
            if state.state == RuntimeState.PAUSED:
                act_pause_resume.setText("Resume")
                act_pause_resume.setEnabled(True)
            elif state.state == RuntimeState.RUNNING:
                act_pause_resume.setText("Pause")
                act_pause_resume.setEnabled(True)
            else:
                act_pause_resume.setText("Pause")
                act_pause_resume.setEnabled(False)
        if act_show_hide is not None:
            act_show_hide.setText("Hide Overlay" if overlay.isVisible() else "Show Overlay")
        if act_settings is not None:
            act_settings.setEnabled(state.state != RuntimeState.STARTING)
        if act_open_logs is not None:
            act_open_logs.setEnabled(True)

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
                "Invalid Settings",
                "Device ID must be blank or an integer.",
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

    def _test_mic() -> None:
        # Lightweight visual pulse until full meter wiring is added.
        main_window.set_meter_level(random.randint(8, 92))

    if QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        icon = app.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        tray = QtWidgets.QSystemTrayIcon(icon, app)
        tray.setToolTip("ItoSub")
        menu = QtWidgets.QMenu()
        act_show_app = menu.addAction("Show App")
        menu.addSeparator()
        act_start_stop = menu.addAction("Start")
        act_pause_resume = menu.addAction("Pause")
        act_show_hide = menu.addAction("Show Overlay")
        act_settings = menu.addAction("Settings")
        act_open_logs = menu.addAction("Open Logs")
        menu.addSeparator()
        act_quit = menu.addAction("Quit")
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

    timer = QtCore.QTimer()

    def _on_tick() -> None:
        _drain_subtitle_bus(bus, overlay, max(1, int(args.max_updates_per_tick)))

        if state.state in (RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.STARTING):
            main_window.set_meter_level(random.randint(4, 36))
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
        overlay.add_line(
            SubtitleLine(
                en="Worker crashed. See console log.",
                ja="\u30ef\u30fc\u30ab\u30fc\u304c\u505c\u6b62\u3057\u307e\u3057\u305f\u3002\u30b3\u30f3\u30bd\u30fc\u30eb\u30ed\u30b0\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
            )
        )
        main_window.show()
        main_window.activateWindow()
        _sync_window_state()
        _refresh_tray_actions()

    timer.timeout.connect(_on_tick)
    timer.start(max(10, int(args.poll_ms)))

    def _on_about_to_quit() -> None:
        logger.info("app_quit")
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
