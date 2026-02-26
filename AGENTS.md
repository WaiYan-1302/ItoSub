# ItoSub Agent Guide

## Project State (2026-02-26)
- Milestone 4A complete: live mic ASR stabilized with utterance finalization (no per-chunk decode).
- Milestone 4B complete: finalized ASR utterances can be translated live.
- Milestone 5 runnable: WebRTC VAD + utterance chunker demo exists and remains a quality/perf baseline.
- Milestone 6A/6B complete: PyQt overlay + live ASR/translation bridge are implemented.
- Milestone 7 in progress: app runtime, tray, settings, config, and logging baseline are implemented.

## Locked Decisions
- Never run faster-whisper per small live chunk.
- Always buffer into utterances and transcribe once per finalized utterance.
- Keep contracts from `itosub/contracts.py`.
- `ASRSegment` must use `t0` and `t1`.
- Do not disable whisper `no_speech_threshold` globally.

## Working Device and Presets
- Common working mic device on this machine: `--device 1`.

## Current Preferred Translation Tuning (User-confirmed good)
- Keep this as the default starting profile for live overlay translation quality on this machine.
- First run can still be slower due to warmup; evaluate responsiveness from second run onward.

### Preferred app command
```powershell
python -m itosub.app.main --device 1 --sr 48000 --model base --translator argos --async-translate --silence-chunks 1 --gap-sec 0.8 --hard-max-chars 120 --poll-ms 30 --max-updates-per-tick 50
```

### Optional adjustment
- If short phrases are being missed, add:
  - `--min-utter-sec 0.3`

### Practical notes
- Keep `--translator stub` available to isolate UI/ASR timing from translation latency.
- `--poll-ms 30` and higher `--max-updates-per-tick` help overlay catch up when translation backlogs.

### Quality-first ASR-only
```powershell
python -m itosub.demos.demo_live_mic_transcribe --config itosub/live_mic.json
```

### Quality-first ASR+translation (Argos)
```powershell
python -m itosub.demos.demo_live_mic_asr_translate --config itosub/live_mic.json --translator argos
```

### Milestone 5 VAD chunker demo
```powershell
python -m itosub.demos.demo_live_mic_translate_vad --device 1 --sr 48000 --channels 1 --chunk-sec 0.5 --model base --translator argos --vad 1 --frame-ms 20 --min-speech-ms 260 --end-silence-ms 750 --gap-sec 0.9 --hard-max-chars 140
```

## Milestone 6 (Overlay) Current State
- Overlay module: `itosub/ui/overlay_qt.py`
- Bridge module: `itosub/ui/bridge.py`
- Live overlay demo compatibility wrapper: `itosub/demos/demo_live_overlay_translate.py`
- Overlay tests: `tests/test_overlay_format.py`, `tests/test_overlay_bridge.py`

### Overlay behavior
- Always-on-top, frameless, translucent.
- Stacked JA/EN lines.
- Hotkeys: `H` toggle EN, `+/-` font size, `P` pause, `ESC` quit.
- UI integration uses queue + `QTimer` polling on UI thread.

## Milestone 7 Roadmap (Windows-first)
### Plan
1. 7A1 Runtime extraction into `itosub/app/runtime.py` and services modules.
2. 7A2 Product entrypoint in `itosub/app/main.py`.
3. 7B Config system: defaults < user config < CLI.
4. 7C Logging/crash diagnostics polish.
5. 7D Tray integration and runtime controls.
6. 7E Settings UX polish.
7. 7F Windows packaging (PyInstaller one-folder first).

### Execution Status (2026-02-26)
- Completed:
  - 7A1 runtime extraction done.
  - 7A2 app entrypoint done (`python -m itosub.app.main`).
  - 7B baseline config done (`itosub/app/config.py`, `assets/config/default.json`).
  - 7D baseline tray done: Show App, Start/Stop, Pause/Resume, Show/Hide Overlay, Settings, Open Logs, Quit.
  - 7E baseline settings done: sections + save/load + runtime apply/restart logic.
  - Main window baseline done: status line, Start/Stop, Settings, Test Mic, mic meter card.
  - Windows startup stability fix done: preload ASR runtime before PyQt import (avoids intermittent `torch c10.dll` `WinError 1114`).
  - Audio/settings update done: real RMS mic meter monitor, input-device dropdown + refresh, overlay opacity + position preset controls.
  - Settings overlay live preview implemented (style controls update preview immediately before Save).
  - ASR language lock implemented end-to-end (`language_lock`: `auto|en`) across config, settings UI, services wiring, and tests.
  - 7C diagnostics baseline implemented: UI popups now include concise error cause + hint + log path for ASR preload failures and worker crashes.
  - Overlay interaction update implemented: resizable overlay, improved drag behavior (no accidental text selection while dragging), and selectable-text default set to off.
  - Hotkeys are now user-editable via Settings (toggle EN, font +/-, pause, quit, toggle selectable text).
  - User-facing naming updated in settings: "ASR" section shown as "Speech Recognition".
  - UI language setting implemented (`ui_language`: `en|ja`) and wired to main window labels/status text.
  - Mic meter display sensitivity reduced with display gain `0.4`.
  - Start-time loading indicator implemented on overlay while worker/transcriber warmup runs; indicator hides when runtime is ready.
  - Translator product default is now `argos`; legacy `stub` values are auto-migrated to `argos` in app config loading.
  - Preset system implemented in Settings: built-in profiles + custom named presets saved from current settings.
- Pending:
  - 7C: diagnostics polish pass (expand hint coverage and add optional quick-copy/open-log actions in popup).
  - 7E: remaining settings polish (tooltip/help text and minor UX cleanup).
  - 7F: packaging + installer script.

## Runtime and UX Notes for Future Agents
- Keep ASR preload before any PyQt import in `itosub/app/main.py`.
- Keep heavy ASR/translation off UI thread; UI only drains queue and updates widgets.
- Overlay loading UX: show loading indicator during start/warmup to avoid blank-box confusion, then hide on worker-ready signal.
- Keep overlay module independent from ASR/translation logic.
- Keep overlay position behavior:
  - presets: `bottom_center`, `bottom_left`, `top_center`
  - `custom` should preserve dragged position.
- Config keys added for overlay controls:
  - `overlay_opacity` (0-100)
  - `overlay_position` (`bottom_center|bottom_left|top_center|custom`)
  - `overlay_text_selectable` (default `false`)
  - editable hotkeys: `hotkey_toggle_en`, `hotkey_font_inc`, `hotkey_font_dec`, `hotkey_pause`, `hotkey_quit`, `hotkey_toggle_selectable`
  - `ui_language` (`en|ja`) for app UI language
  - Translator note: do not expose `stub` in product Settings; keep runtime default as `argos`.
  - Preset persistence keys: `active_preset`, `custom_presets`.
  - Note: after changing `ui_language` in Settings and saving, reopen Settings dialog to see all labels in the new language.

## Known Environment Notes
- `webrtcvad` may fail if `pkg_resources` is missing. If needed:
  - `python -m pip install --force-reinstall "setuptools<81"`
  - or install `webrtcvad-wheels`.
- HuggingFace symlink warning on Windows is non-fatal.
- Argos warning about `mwt` is informational and non-fatal.

## Scope Rules
### Allowed read/write
- `itosub/**`
- `tests/**`
- `pyproject.toml`
- `README.md`
- `AGENTS.md`

### Allowed read-only
- `assets/**` (may write new WAVs under `assets/audio/`)

### Ignore completely
- `.venv/**`
- `site-packages/**`
- `itosub.egg-info/**`
- `.idea/**`
- `**/__pycache__/**`
- `**/*.pyc`
- `.pytest_cache/**`
- `.mypy_cache/**`
- `.ruff_cache/**`
- `build/**`
- `dist/**`
- `*.log`

## Safety Constraints
- Do not break Milestone 1-3 demos/tests.
- Keep modules small and testable.
- Prefer additive changes over rewrites.

## Next Priorities
1. 7C diagnostics polish: add quick-copy/open-log actions and broader hint mapping.
2. Prepare 7F packaging profile and installer checklist.
3. Add small UX polish pass (settings tooltips + labels consistency).
