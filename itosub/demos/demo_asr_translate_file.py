from __future__ import annotations

import argparse

from itosub.asr.faster_whisper_file import FasterWhisperFileTranscriber
from itosub.contracts import TranslationRequest
from itosub.nlp.translator.factory import get_translator


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav_path", help="Path to WAV file")
    ap.add_argument("--model", default="tiny", help="tiny|base|small|medium|large-v3")
    ap.add_argument("--lang", default="en", help="ASR language (en recommended)")
    ap.add_argument("--translator", default="stub", help="stub|argos (or set ITOSUB_TRANSLATOR)")
    ap.add_argument("--join", action="store_true", help="Translate the whole transcript at once")
    args = ap.parse_args()

    asr = FasterWhisperFileTranscriber(model_size=args.model, language=args.lang)
    tr = get_translator(args.translator)

    segs = asr.transcribe_file(args.wav_path)

    if args.join:
        full_en = " ".join(s.text for s in segs)
        res = tr.translate(TranslationRequest(text=full_en))
        print("---- EN (full) ----")
        print(full_en)
        print("---- JA (full) ----")
        print(res.translated_text)
        return 0

    # Translate segment-by-segment (better for subtitle flow)
    for i, s in enumerate(segs, 1):
        res = tr.translate(TranslationRequest(text=s.text))
        print(f"{i:02d} [{s.t0:6.2f} → {s.t1:6.2f}]")
        print(f"EN: {s.text}")
        print(f"JA: {res.translated_text}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())