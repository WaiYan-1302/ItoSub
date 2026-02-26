from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from itosub.asr.faster_whisper_pcm16 import FasterWhisperPCM16Transcriber
from itosub.audio.mic import SoundDeviceMicSource
from itosub.audio.vad import EnergyVAD
from itosub.live.live_transcribe import LiveUtteranceTranscriber


_DEFAULTS: Dict[str, Any] = {
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
}


def _load_config(path: str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded, dict):
        raise ValueError("config must be a JSON object")
    return loaded


def _parser_with_defaults(defaults: Dict[str, Any]) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None, help="JSON config path (CLI flags override config)")
    p.add_argument("--list-devices", action="store_true", help="print audio devices and exit")
    p.add_argument("--device", type=int, default=defaults["device"], help="sounddevice input device id")
    p.add_argument("--sr", type=int, default=defaults["sr"], help="sample rate (Hz)")
    p.add_argument("--channels", type=int, default=defaults["channels"], help="input channels")
    p.add_argument(
        "--chunk-sec", type=float, default=defaults["chunk_sec"], help="mic chunk size in seconds"
    )
    p.add_argument(
        "--rms-th", type=float, default=defaults["rms_th"], help="RMS threshold for speech VAD"
    )
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
    return p


def _resolve_args(argv: list[str] | None = None) -> argparse.Namespace:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", default=None)
    pre_args, _ = pre.parse_known_args(argv)

    defaults = dict(_DEFAULTS)
    if pre_args.config:
        try:
            loaded = _load_config(pre_args.config)
        except Exception as e:  # pragma: no cover - parser error path
            raise SystemExit(f"Failed to load config '{pre_args.config}': {e}") from e

        for key in _DEFAULTS.keys():
            if key in loaded:
                defaults[key] = loaded[key]

    parser = _parser_with_defaults(defaults)
    args = parser.parse_args(argv)

    if args.config and defaults.get("list_devices"):
        args.list_devices = True
    if args.config and defaults.get("debug"):
        args.debug = True

    return args


def main(argv: list[str] | None = None) -> int:
    args = _resolve_args(argv)

    if args.list_devices:
        print(SoundDeviceMicSource.list_devices())
        return 0

    mic = SoundDeviceMicSource(
        chunk_seconds=args.chunk_sec,
        sample_rate=args.sr,
        channels=args.channels,
        device=args.device,
    )
    vad = EnergyVAD(rms_threshold=args.rms_th)
    transcriber = FasterWhisperPCM16Transcriber(model_size=args.model, language="en")

    def on_asr(t0: float, t1: float, text: str) -> None:
        print(f"[utt {t0:.2f}-{t1:.2f}] {text}")

    runner = LiveUtteranceTranscriber(
        chunk_iter=mic.chunks(),
        transcriber=transcriber,
        vad=vad,
        on_asr=on_asr,
        silence_chunks_to_finalize=args.silence_chunks,
        min_utter_sec=args.min_utter_sec,
        max_utter_sec=args.max_utter_sec,
        debug=args.debug,
    )

    print("ItoSub live ASR (utterance mode). Press Ctrl+C to stop.")
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
