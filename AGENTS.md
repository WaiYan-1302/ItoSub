# ItoSub Agent Guide

## Project State (2026-02-25)
- Milestone 4A complete: live mic ASR is stable with utterance finalization (no per-chunk decode).
- Milestone 4B bridge complete: finalized ASR utterances can be translated live.
- Milestone 5 in progress and runnable: WebRTC VAD + utterance chunker demo exists and runs.
- Product decision: delay is acceptable if transcription quality is preserved.

## Milestone 6 (PyQt Overlay) ÅECurrent State

### What Milestone 6 means
- UI-only milestone: PyQt subtitle overlay.
- Always-on-top, frameless, translucent background.
- Shows JA (optionally EN) as stacked subtitle lines.
- Supports hotkeys: toggle EN, font size +/-, pause, quit.
- Exposes simple update API (e.g., `add_line(en, ja)`).

### Completion status
- Milestone 6A achieved: overlay module + smoke demo + minimal non-GUI test.
- Milestone 6B achieved: live ASR/translation is wired to overlay via worker thread + queue + UI polling.

### Milestone 6 code locations
- `itosub/ui/overlay_qt.py`
- `itosub/ui/bridge.py`
- `itosub/demos/demo_overlay_smoke.py`
- `itosub/demos/demo_live_overlay_translate.py`
- `tests/test_overlay_format.py` (or equivalent non-GUI formatting test)
- `tests/test_overlay_bridge.py`

### Milestone 6 constraints
- Do NOT start Milestone 6B unless explicitly requested.
- Keep overlay module independent from ASR/translation logic.
- Keep UI responsive; never run heavy work on Qt UI thread.
- Keep Milestone 1ÅE demos/tests working.

### Milestone 6B design (implemented)
- ASR+translation runs in worker thread/process.
- UI thread polls queue via `QTimer` and calls `overlay.add_line(...)`.
- Command: `python -m itosub.demos.demo_live_overlay_translate --config itosub/live_mic.json --translator argos`

### Milestone 6B latency tuning log (2026-02-25)
- Root cause observed: overlay path felt slower than Milestone 5 when translation backlog built up.
- Implementation update made in demo_live_overlay_translate.py:
  - Added pre-translation SubtitleSegmenter commit flow (gap_sec, hard_max_chars) so translation is not called for every tiny ASR fragment.
  - Added Milestone-5-style EN cleanup before translation (_dedupe_repeated_words, low-value fragment skip).
  - Kept async translation mode (--async-translate) so EN can display first and JA arrives when ready.

#### Commands tested and outcomes
- Underperformed / unstable for this machine/session:
  - python -m itosub.demos.demo_live_overlay_translate --config itosub/live_mic.json --translator argos --async-translate --silence-chunks 1 --gap-sec 0.8 --hard-max-chars 120
  - Observation: first run could be barely transcribing/translation felt delayed.
- Worked well after warmup:
  - python -m itosub.demos.demo_live_overlay_translate --config itosub/live_mic.json --translator argos --async-translate --silence-chunks 1 --min-utter-sec 0.3 --gap-sec 0.8 --hard-max-chars 120 --poll-ms 30 --max-updates-per-tick 50
  - Observation: good responsiveness and usable translation timing after second run.
- Current preferred command (best balance, user-confirmed very good):
  - python -m itosub.demos.demo_live_overlay_translate --config itosub/live_mic.json --translator argos --async-translate --silence-chunks 1 --gap-sec 0.8 --hard-max-chars 120 --poll-ms 30 --max-updates-per-tick 50
  - Note: add --min-utter-sec 0.3 only when short phrases are being missed.

#### Practical notes
- First run is often slower due to model/translator warmup; evaluate latency from second run onward.
- --poll-ms 30 and higher --max-updates-per-tick improved overlay catch-up behavior.
- Keep --translator stub available for isolating UI/ASR timing from translation latency.
## Locked Decisions
- Never run faster-whisper per small live chunk.
- Always buffer into utterances and transcribe once per finalized utterance.
- Keep contracts from `itosub/contracts.py`.
- `ASRSegment` must use `t0` and `t1`.
- Do not disable whisper `no_speech_threshold` globally.

## Working Device and Presets
- Mic device on this machine: `--device 1`.

### Quality-first ASR-only (delay allowed)
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

### Faster but lower quality profile
```powershell
python -m itosub.demos.demo_live_mic_translate_vad --device 1 --sr 16000 --channels 1 --chunk-sec 0.4 --model tiny --translator argos --vad 1 --frame-ms 20 --min-speech-ms 220 --end-silence-ms 550 --gap-sec 0.8 --hard-max-chars 120
```

## Current Milestone 5 Files
- `itosub/audio/vad_webrtc.py`
- `itosub/audio/utterance_chunker.py`
- `itosub/demos/demo_live_mic_translate_vad.py`

## Known Environment Notes
- `webrtcvad` may fail if `pkg_resources` is missing. If needed:
  - `python -m pip install --force-reinstall "setuptools<81"`
  - or install `webrtcvad-wheels`.
- HuggingFace symlink warning on Windows is non-fatal. Optional suppress:
  - `$env:HF_HUB_DISABLE_SYMLINKS_WARNING="1"`
- Argos warning about `mwt` is informational and non-fatal.

## Performance Reality
- First run is slow due to model warmup/loading.
- `--model base/small` improves ASR quality but increases latency.
- `--translator argos` adds noticeable per-line latency.
- For responsiveness debugging, use `--translator stub`.

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

## Milestone 7 Roadmap (Windows-first)
### Plan (approved)
1. 7A1 Runtime extraction: move live overlay worker/pipeline logic from demo into itosub.app runtime/services modules.
2. 7A2 Product entrypoint: add itosub/app/main.py as official app startup path; keep demo command as compatibility wrapper.
3. 7B Config system: defaults in assets/config/default.json; user config in %APPDATA%\\ItoSub\\config.json; precedence = defaults < user config < CLI.
4. 7C Logging/crash diagnostics: next step (pending).
5. 7D Tray integration: next step (pending).
6. 7E Minimal settings UI: recommended before packaging (pending).
7. 7F Windows packaging: PyInstaller one-folder first (pending).

### Execution Status (2026-02-25)
- Completed now:
  - 7A1 implemented (itosub/app/runtime.py, itosub/app/services.py).
  - 7A2 implemented (itosub/app/main.py, runnable via python -m itosub.app.main).
  - 7B implemented baseline (itosub/app/config.py, assets/config/default.json).
  - itosub/demos/demo_live_overlay_translate.py now delegates to app entrypoint while preserving test helper exports.
- Pending next:
  - 7C logging file/rotation + latency metrics fields.
  - 7D tray icon actions (Pause/Show/Hide/Open Logs/Quit).
  - 7E settings dialog + config save flow.
  - 7F packaging + installer script.
## Milestone 7 UX Direction (2026-02-25, approved)
### Product flow decision
- Chosen flow for v1: Option B + tray integration.
- Startup shows a minimal main window with Start, Settings, Test Mic, status line, and mic meter.
- On Start: launch overlay + live pipeline, then minimize main window to tray.
- Tray menu (v1): Start/Stop, Pause/Resume, Settings, Quit.

### UX/visual direction
- Modern minimalist dark UI.
- Settings-first experience after first launch, but no wizard required for v1.
- Settings dialog layout: left sidebar + right content panel.
- Sidebar sections: Audio, ASR, Translation, Overlay, Hotkeys, Advanced.
- Right panel includes controls + small live overlay preview.
- Footer buttons: Restore Defaults, Cancel, Save.

### v1 settings scope (must-have only)
- Audio: device selection, refresh, input level meter, sensitivity.
- ASR: model size (tiny/base/small), language lock (auto/en).
- Translation: provider (Argos), join-fragments-before-translation toggle.
- Overlay: background opacity, JP font size, show EN toggle, position preset.

### Runtime and implementation notes
- Introduce explicit runtime states: stopped, starting, running, paused, error.
- Keep one config schema source of truth in itosub.app.config with migration-safe defaults.
- Keep overlay as separate window (frameless, always-on-top, draggable).

### Planned implementation order (next session)
1. 7D tray controller and runtime state actions.
2. 7E settings dialog with save/load bindings.
3. Main window polish (status + mic meter + Start/Test Mic).
4. 7C structured logging surfaced in UI.
5. 7F Windows packaging.
## Next Priorities
1. Keep Milestone 5 stable and tune VAD/commit parameters for quality.
2. Add optional async translation mode so EN prints immediately and JA arrives later.
3. Add repeatable evaluation checklist (missed words, latency, false triggers).
4. Improve overlay UX polish and add integration smoke checks for the live overlay path.
