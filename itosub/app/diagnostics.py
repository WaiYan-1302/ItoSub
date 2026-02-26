from __future__ import annotations


def summarize_exception(detail: str, *, max_len: int = 220) -> str:
    text = str(detail or "").strip()
    if not text:
        return "Unknown runtime error."
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "Unknown runtime error."
    for ln in reversed(lines):
        if ln.startswith("File "):
            continue
        if ln.startswith("^"):
            continue
        if ln.startswith("Traceback "):
            continue
        out = ln
        break
    else:
        out = lines[-1]
    if len(out) > max_len:
        return out[: max_len - 3].rstrip() + "..."
    return out


def hint_for_exception(summary: str) -> str:
    s = str(summary or "").lower()
    if "winerror 1114" in s or "c10.dll" in s:
        return "Torch DLL init failed. Restart app; if persistent, reinstall CPU torch in this venv."
    if "no module named" in s:
        return "A required package is missing in this virtualenv. Reinstall dependencies and retry."
    if "config file not found" in s:
        return "Configured JSON file is missing. Update the config path or restore the file."
    if "sounddevice" in s and "failed" in s:
        return "Microphone init failed. Check input device selection and app mic permissions."
    return "Check logs for full traceback."
