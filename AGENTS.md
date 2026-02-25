# ItoSub Agent Guide

## Project State (2026-02-25)
- Milestone 4A complete: live mic ASR is stable when using utterance finalization (not per-chunk decode).
- Milestone 4B bridge complete: finalized ASR utterances can be translated live.
- Milestone 5 in progress and runnable: WebRTC VAD + utterance chunker demo exists and runs.
- Product decision: delay is acceptable if transcription quality is preserved.

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

## Next Priorities
1. Keep Milestone 5 stable and tune VAD/commit parameters for quality.
2. Add optional async translation mode so EN prints immediately and JA arrives later.
3. Add repeatable evaluation checklist (missed words, latency, false triggers).
4. Defer UI/overlay work until ASR+translation quality is accepted.
