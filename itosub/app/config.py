from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from platformdirs import user_config_dir
except ModuleNotFoundError:  # pragma: no cover
    def user_config_dir(appname: str, appauthor: str | None = None) -> str:
        del appauthor
        appdata = os.getenv("APPDATA")
        if appdata:
            return str(Path(appdata) / appname)
        return str(Path.home() / ".config" / appname)


DEFAULTS: dict[str, Any] = {
    "list_devices": False,
    "device": None,
    "sr": 16000,
    "channels": 1,
    "chunk_sec": 0.5,
    "rms_th": 250.0,
    "silence_chunks": 2,
    "min_utter_sec": 0.6,
    "max_utter_sec": 6.0,
    "debug": False,
    "model": "tiny",
    "translator": "stub",
    "show_en": True,
    "max_lines": 4,
    "font_size_ja": 28,
    "font_size_en": 16,
    "padding_px": 14,
    "poll_ms": 60,
    "queue_maxsize": 100,
    "max_updates_per_tick": 20,
    "print_console": True,
    "async_translate": True,
    "gap_sec": 0.9,
    "hard_max_chars": 140,
}
CONFIG_KEYS: tuple[str, ...] = tuple(DEFAULTS.keys())


@dataclass(frozen=True)
class AppPaths:
    config_dir: Path
    config_path: Path


def default_asset_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "config" / "default.json"


def app_paths() -> AppPaths:
    config_dir = Path(user_config_dir("ItoSub", "ItoSub"))
    return AppPaths(config_dir=config_dir, config_path=config_dir / "config.json")


def _load_json_dict(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded, dict):
        raise ValueError(f"config must be a JSON object: {path}")
    return loaded


def _write_json_dict(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _known_only(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in CONFIG_KEYS:
        if key in payload:
            out[key] = payload[key]
    return out


def load_default_config() -> dict[str, Any]:
    path = default_asset_config_path()
    if not path.exists():
        return dict(DEFAULTS)
    loaded = _load_json_dict(path)
    out = dict(DEFAULTS)
    for key in DEFAULTS.keys():
        if key in loaded:
            out[key] = loaded[key]
    return out


def load_user_config(config_path: str | None = None) -> tuple[dict[str, Any], Path]:
    defaults = load_default_config()
    if config_path:
        chosen = Path(config_path)
        if not chosen.exists():
            raise SystemExit(f"Config file not found: {chosen}")
        loaded = _known_only(_load_json_dict(chosen))
        merged = dict(defaults)
        merged.update(loaded)
        return merged, chosen

    chosen = ensure_user_config_exists(defaults)
    loaded = _known_only(_load_json_dict(chosen))
    merged = dict(defaults)
    merged.update(loaded)
    return merged, chosen


def save_user_config(values: dict[str, Any], config_path: str | None = None) -> Path:
    payload = _known_only(values)
    if config_path:
        path = Path(config_path)
        existing = _known_only(_load_json_dict(path)) if path.exists() else {}
        merged = dict(load_default_config())
        merged.update(existing)
        merged.update(payload)
        _write_json_dict(path, _known_only(merged))
        return path

    defaults = load_default_config()
    path = ensure_user_config_exists(defaults)
    existing = _known_only(_load_json_dict(path))
    merged = dict(defaults)
    merged.update(existing)
    merged.update(payload)
    _write_json_dict(path, _known_only(merged))
    return path


def ensure_user_config_exists(defaults: dict[str, Any] | None = None) -> Path:
    paths = app_paths()
    if paths.config_path.exists():
        return paths.config_path
    _write_json_dict(paths.config_path, defaults or load_default_config())
    return paths.config_path


def resolve_defaults(config_path: str | None = None) -> tuple[dict[str, Any], Path]:
    return load_user_config(config_path=config_path)


def parser_with_defaults(defaults: dict[str, Any]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None, help="JSON config path (CLI flags override config)")
    p.add_argument("--list-devices", action="store_true", help="print audio devices and exit")
    p.add_argument("--device", type=int, default=defaults["device"], help="sounddevice input device id")
    p.add_argument("--sr", type=int, default=defaults["sr"], help="sample rate (Hz)")
    p.add_argument("--channels", type=int, default=defaults["channels"], help="input channels")
    p.add_argument("--chunk-sec", type=float, default=defaults["chunk_sec"], help="mic chunk size in seconds")
    p.add_argument("--rms-th", type=float, default=defaults["rms_th"], help="RMS threshold for speech VAD")
    p.add_argument(
        "--silence-chunks",
        type=int,
        default=defaults["silence_chunks"],
        help="finalize after this many non-speech chunks",
    )
    p.add_argument(
        "--min-utter-sec",
        type=float,
        default=defaults["min_utter_sec"],
        help="ignore utterances shorter than this",
    )
    p.add_argument(
        "--max-utter-sec",
        type=float,
        default=defaults["max_utter_sec"],
        help="force finalize while continuously speaking (seconds)",
    )
    p.add_argument("--debug", action="store_true", help="print chunk RMS and speech decisions")
    p.add_argument("--model", default=defaults["model"], help="faster-whisper model size")
    p.add_argument("--translator", default=defaults["translator"], help="stub|argos")
    p.add_argument(
        "--show-en",
        action=argparse.BooleanOptionalAction,
        default=defaults["show_en"],
        help="show/hide English subtitle line in overlay",
    )
    p.add_argument("--max-lines", type=int, default=defaults["max_lines"], help="visible subtitle lines")
    p.add_argument("--font-size-ja", type=int, default=defaults["font_size_ja"], help="Japanese font size")
    p.add_argument("--font-size-en", type=int, default=defaults["font_size_en"], help="English font size")
    p.add_argument("--padding-px", type=int, default=defaults["padding_px"], help="overlay panel padding")
    p.add_argument("--poll-ms", type=int, default=defaults["poll_ms"], help="UI queue poll interval (ms)")
    p.add_argument(
        "--queue-maxsize",
        type=int,
        default=defaults["queue_maxsize"],
        help="max subtitle queue size between worker and UI",
    )
    p.add_argument(
        "--max-updates-per-tick",
        type=int,
        default=defaults["max_updates_per_tick"],
        help="max subtitles to apply per UI timer tick",
    )
    p.add_argument(
        "--print-console",
        action=argparse.BooleanOptionalAction,
        default=defaults["print_console"],
        help="print committed EN/JA lines to console",
    )
    p.add_argument(
        "--async-translate",
        action=argparse.BooleanOptionalAction,
        default=defaults["async_translate"],
        help="show EN immediately and translate JA in background",
    )
    p.add_argument("--gap-sec", type=float, default=defaults["gap_sec"], help="segmenter pause boundary")
    p.add_argument(
        "--hard-max-chars",
        type=int,
        default=defaults["hard_max_chars"],
        help="segmenter emergency commit limit",
    )
    return p


def resolve_args(argv: list[str] | None = None) -> argparse.Namespace:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", default=None)
    pre_args, _ = pre.parse_known_args(argv)
    defaults, _ = resolve_defaults(config_path=pre_args.config)
    parser = parser_with_defaults(defaults)
    args = parser.parse_args(argv)
    if defaults.get("list_devices"):
        args.list_devices = True
    if defaults.get("debug"):
        args.debug = True
    return args
