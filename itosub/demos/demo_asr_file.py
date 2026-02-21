from __future__ import annotations
import argparse
from itosub.asr.faster_whisper_file import FasterWhisperFileTranscriber

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav_path", help="Path to a WAV file")
    ap.add_argument("--model", default="base", help="tiny|base|small|medium|large-v3 (CPU: tiny/base/small recommended)")
    ap.add_argument("--lang", default="en", help="Language code, e.g., en")
    args = ap.parse_args()

    asr = FasterWhisperFileTranscriber(model_size=args.model, language=args.lang)
    segs = asr.transcribe_file(args.wav_path)

    for i, s in enumerate(segs, 1):
        print(f"{i:02d} [{s.t0:6.2f} → {s.t1:6.2f}] {s.text}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())