from __future__ import annotations

import argparse
import wave
from pathlib import Path

from itosub.audio.mic import SoundDeviceMicSource


class MicRecordError(RuntimeError):
    pass


def _record_pcm16(*, device: int | None, sample_rate: int, channels: int, seconds: float) -> bytes:
    try:
        import sounddevice as sd
    except ImportError as e:
        raise MicRecordError(
            "sounddevice is not installed. Install with: python -m pip install sounddevice"
        ) from e

    total_frames = int(round(sample_rate * seconds))
    if total_frames <= 0:
        return b""

    frames_per_read = min(4096, max(1, sample_rate // 10))
    captured = bytearray()
    frames_captured = 0

    stream = sd.RawInputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
        device=device,
        blocksize=0,
    )

    with stream:
        while frames_captured < total_frames:
            to_read = min(frames_per_read, total_frames - frames_captured)
            data, overflowed = stream.read(to_read)
            if overflowed:
                pass
            captured.extend(data)
            frames_captured += to_read

    return bytes(captured)


def _write_wav(path: Path, pcm16: bytes, sample_rate: int, channels: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--device", type=int, default=None, help="sounddevice input device id")
    p.add_argument("--sr", type=int, default=48000, help="sample rate (Hz)")
    p.add_argument("--channels", type=int, default=1, help="input channels")
    p.add_argument("--seconds", type=float, default=8.0, help="recording duration")
    p.add_argument("--out", default="assets/audio/mic_test.wav", help="output WAV path")
    p.add_argument("--list-devices", action="store_true", help="print audio devices and exit")
    args = p.parse_args()

    if args.list_devices:
        print(SoundDeviceMicSource.list_devices())
        return 0

    out_path = Path(args.out)
    print(f"Recording {args.seconds:.1f}s from device={args.device} sr={args.sr} ch={args.channels}...")
    pcm16 = _record_pcm16(
        device=args.device,
        sample_rate=args.sr,
        channels=args.channels,
        seconds=args.seconds,
    )
    _write_wav(out_path, pcm16, sample_rate=args.sr, channels=args.channels)

    print(f"Saved WAV: {out_path}")
    print("Please listen to this file to verify microphone capture quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
