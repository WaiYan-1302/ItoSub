from __future__ import annotations

import argparse
import time
import numpy as np

from itosub.audio.mic import SoundDeviceMicSource


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chunk-sec", type=float, default=0.5)
    p.add_argument("--sr", type=int, default=16000)
    p.add_argument("--device", type=int, default=None)
    p.add_argument("--list-devices", action="store_true")
    p.add_argument("--seconds", type=float, default=5.0)
    args = p.parse_args()

    if args.list_devices:
        print(SoundDeviceMicSource.list_devices())
        return 0

    mic = SoundDeviceMicSource(
        chunk_seconds=args.chunk_sec,
        sample_rate=args.sr,
        channels=1,
        device=args.device,
    )

    print("Speak into the mic now... (Ctrl+C to stop)")
    t_end = time.time() + args.seconds

    for chunk in mic.chunks():
        x = np.frombuffer(chunk.pcm16, dtype=np.int16).astype(np.float32)
        peak = float(np.max(np.abs(x))) if x.size else 0.0
        rms = float(np.sqrt(np.mean(x * x))) if x.size else 0.0

        print(f"peak={peak:8.1f}  rms={rms:8.1f}")

        if time.time() >= t_end:
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())