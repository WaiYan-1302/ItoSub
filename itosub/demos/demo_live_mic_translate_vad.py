from __future__ import annotations

import argparse
import re

from itosub.asr.faster_whisper_pcm16 import FasterWhisperPCM16Transcriber
from itosub.audio.mic import SoundDeviceMicSource
from itosub.audio.utterance_chunker import UtteranceConfig, utterances_from_audio_chunks
from itosub.contracts import TranslationRequest
from itosub.nlp.segmenter import SubtitleSegmenter
from itosub.nlp.translator.factory import get_translator


_PUNCT_END = re.compile(r"[.!?]$")


def _dedupe_repeated_words(text: str, max_repeat: int = 2) -> str:
    words = text.split()
    if not words:
        return ""
    out = []
    prev = None
    run = 0
    for w in words:
        wl = w.lower()
        if wl == prev:
            run += 1
        else:
            prev = wl
            run = 1
        if run <= max_repeat:
            out.append(w)
    return " ".join(out).strip()


def _is_low_value_fragment(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    words = t.split()
    if len(words) == 1 and not _PUNCT_END.search(t):
        return True
    if len(t) <= 2:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--device", type=int, default=None)
    ap.add_argument("--sr", type=int, default=16000)
    ap.add_argument("--channels", type=int, default=1)
    ap.add_argument("--chunk-sec", type=float, default=0.5)
    ap.add_argument("--model", default="base")
    ap.add_argument("--translator", default="argos", help="stub|argos")
    ap.add_argument("--vad", type=int, default=2, help="0..3 (higher = stricter)")
    ap.add_argument("--frame-ms", type=int, default=20, help="10/20/30")
    ap.add_argument("--min-speech-ms", type=int, default=200)
    ap.add_argument("--end-silence-ms", type=int, default=500)
    ap.add_argument("--gap-sec", type=float, default=0.8, help="segmenter pause boundary")
    ap.add_argument("--hard-max-chars", type=int, default=160, help="segmenter hard commit limit")
    args = ap.parse_args()

    if args.list_devices:
        print(SoundDeviceMicSource.list_devices())
        return 0

    mic = SoundDeviceMicSource(
        chunk_seconds=args.chunk_sec,
        sample_rate=args.sr,
        channels=args.channels,
        device=args.device,
    )
    utt_cfg = UtteranceConfig(
        frame_ms=args.frame_ms,
        vad_aggressiveness=args.vad,
        min_speech_ms=args.min_speech_ms,
        end_silence_ms=args.end_silence_ms,
    )
    asr = FasterWhisperPCM16Transcriber(model_size=args.model, language="en")
    tr = get_translator(args.translator)
    segmenter = SubtitleSegmenter(gap_sec=args.gap_sec, hard_max_chars=args.hard_max_chars)

    print("ItoSub live mic -> VAD utterance -> ASR -> translation. Ctrl+C to stop.")
    try:
        for utt in utterances_from_audio_chunks(mic.chunks(), utt_cfg):
            segs = asr.transcribe_utterance(
                utt.pcm16,
                sample_rate=utt.sample_rate,
                channels=utt.channels,
                utter_t0=utt.start_time,
            )
            for s in segs:
                en = _dedupe_repeated_words((s.text or "").strip(), max_repeat=2)
                if _is_low_value_fragment(en):
                    continue
                for line in segmenter.push(en, s.t0, s.t1):
                    ja = tr.translate(TranslationRequest(text=line.text)).translated_text
                    print(f"[utt {line.t0:6.2f}-{line.t1:6.2f}] EN: {line.text}")
                    print(f"[utt {line.t0:6.2f}-{line.t1:6.2f}] JA: {ja}")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        for line in segmenter.flush():
            ja = tr.translate(TranslationRequest(text=line.text)).translated_text
            print(f"[utt {line.t0:6.2f}-{line.t1:6.2f}] EN: {line.text}")
            print(f"[utt {line.t0:6.2f}-{line.t1:6.2f}] JA: {ja}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
