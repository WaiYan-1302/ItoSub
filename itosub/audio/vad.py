from __future__ import annotations

import math
from array import array


def pcm16_rms(pcm16: bytes) -> float:
    """Return RMS energy for little-endian int16 PCM bytes."""
    if not pcm16:
        return 0.0

    samples = array("h")
    samples.frombytes(pcm16)
    if not samples:
        return 0.0

    sum_sq = 0.0
    for value in samples:
        fv = float(value)
        sum_sq += fv * fv
    return math.sqrt(sum_sq / len(samples))


class EnergyVAD:
    def __init__(self, rms_threshold: float = 250.0) -> None:
        if rms_threshold < 0:
            raise ValueError("rms_threshold must be >= 0")
        self.rms_threshold = float(rms_threshold)

    def is_speech(self, pcm16: bytes) -> bool:
        return pcm16_rms(pcm16) >= self.rms_threshold
