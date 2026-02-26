from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from itosub.asr.faster_whisper_pcm16 import FasterWhisperPCM16Transcriber
from itosub.audio.mic import SoundDeviceMicSource
from itosub.audio.vad import EnergyVAD
from itosub.nlp.segmenter import SubtitleSegmenter
from itosub.nlp.translator.factory import get_translator


@dataclass(frozen=True)
class LiveOverlayServices:
    mic: SoundDeviceMicSource
    vad: EnergyVAD
    transcriber: FasterWhisperPCM16Transcriber
    translator: Any
    segmenter: SubtitleSegmenter


def build_live_overlay_services(args: Any) -> LiveOverlayServices:
    mic = SoundDeviceMicSource(
        chunk_seconds=float(args.chunk_sec),
        sample_rate=int(args.sr),
        channels=int(args.channels),
        device=args.device,
    )
    vad = EnergyVAD(rms_threshold=float(args.rms_th))
    transcriber = FasterWhisperPCM16Transcriber(model_size=str(args.model), language="en")
    translator = get_translator(str(args.translator))
    segmenter = SubtitleSegmenter(
        gap_sec=max(0.0, float(args.gap_sec)),
        hard_max_chars=max(20, int(args.hard_max_chars)),
    )
    return LiveOverlayServices(
        mic=mic,
        vad=vad,
        transcriber=transcriber,
        translator=translator,
        segmenter=segmenter,
    )

