from __future__ import annotations

import argparse
import sys
import time
from itosub.nlp.segmenter import SubtitleSegmenter
from itosub.asr.faster_whisper_stream import FasterWhisperStreamTranscriber
from itosub.audio.mic import SoundDeviceMicSource
from itosub.live.pipeline import LiveMicTranslatePipeline
from itosub.nlp.translator.factory import get_translator

# NOTE:
# This assumes your SubtitleSegmenter can do incremental ingest/flush.
# If your current segmenter API differs, add thin wrapper methods there.
from itosub.nlp.segmenter import SubtitleSegmenter


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="tiny", help="faster-whisper model size, e.g., tiny/base/small")
    p.add_argument("--translator", default="argos", help="translator provider, e.g., argos/stub")
    p.add_argument("--chunk-sec", type=float, default=1.5, help="audio chunk size in seconds")
    p.add_argument("--sr", type=int, default=16000, help="microphone sample rate (Hz)")
    p.add_argument("--device", type=int, default=None, help="sounddevice input device id")
    p.add_argument("--list-devices", action="store_true", help="print audio devices and exit")
    p.add_argument("--compute-type", default="int8", help="faster-whisper compute_type (cpu), e.g., int8/float32")
    p.add_argument("--beam-size", type=int, default=1, help="beam size (speed vs quality)")
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

    transcriber = FasterWhisperStreamTranscriber(
        model_size=args.model,
        device="cpu",
        compute_type=args.compute_type,
        language="en",
        beam_size=args.beam_size,
    )

    translator = get_translator(args.translator)

    # You already have this; ensure it supports ingest/flush (see note below).
    segmenter = SubtitleSegmenter()

    t_wall0 = time.time()

    def on_commit(ts: float, en: str, ja: str) -> None:
        wall = time.time() - t_wall0
        print(f"[{wall:7.2f}s] EN: {en}")
        print(f"[{wall:7.2f}s] JA: {ja}")
        print("-" * 60)

    pipeline = LiveMicTranslatePipeline(
        chunk_iter=mic.chunks(),
        transcriber=transcriber,
        segmenter=segmenter,
        translator=translator,
        on_commit=on_commit,
    )

    print("ItoSub Milestone 4: live mic -> EN/JA console subtitles")
    print("Press Ctrl+C to stop.")
    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())