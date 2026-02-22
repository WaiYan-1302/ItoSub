from __future__ import annotations

import argparse
import time

from itosub.asr.faster_whisper_file import FasterWhisperFileTranscriber
from itosub.contracts import TranslationRequest
from itosub.nlp.translator.factory import get_translator
from itosub.nlp.segmenter import SubtitleSegmenter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav_path")
    ap.add_argument("--model", default="tiny")
    ap.add_argument("--translator", default="argos", help="stub|argos")
    ap.add_argument("--speed", type=float, default=1.0, help="1.0 = realtime, 2.0 = 2x faster")
    ap.add_argument("--max-chars", type=int, default=70)
    ap.add_argument("--gap", type=float, default=0.8)
    args = ap.parse_args()

    asr = FasterWhisperFileTranscriber(model_size=args.model, language="en")
    tr = get_translator(args.translator)
    segs = asr.transcribe_file(args.wav_path)

    segmenter = SubtitleSegmenter(max_chars=args.max_chars, gap_sec=args.gap)

    start = time.perf_counter()
    base_t = segs[0].t0 if segs else 0.0

    def wait_until(audio_time: float) -> None:
        # audio_time is in seconds from file start; replay it in wall time
        target = (audio_time - base_t) / max(args.speed, 1e-6)
        while True:
            now = time.perf_counter() - start
            if now >= target:
                return
            time.sleep(0.01)

    for s in segs:
        wait_until(s.t1)  # “subtitle appears” near the end of the spoken segment
        lines = segmenter.push(s.text, s.t0, s.t1)

        for line in lines:
            ja = tr.translate(TranslationRequest(text=line.text)).translated_text
            print(f"[{line.t0:6.2f}→{line.t1:6.2f}] EN: {line.text}")
            print(f"                 JA: {ja}")
            print()

    # flush remaining
    for line in segmenter.flush():
        ja = tr.translate(TranslationRequest(text=line.text)).translated_text
        print(f"[{line.t0:6.2f}→{line.t1:6.2f}] EN: {line.text}")
        print(f"                 JA: {ja}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())