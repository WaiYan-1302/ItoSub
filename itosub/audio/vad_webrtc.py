from __future__ import annotations

from array import array


def _first_channel_mono_pcm16(pcm16: bytes, channels: int) -> bytes:
    if channels <= 1:
        return pcm16
    samples = array("h")
    samples.frombytes(pcm16)
    mono = array("h")
    for i in range(0, len(samples), channels):
        mono.append(samples[i])
    return mono.tobytes()


class WebRtcVad:
    """
    WebRTC VAD expects:
      - 16-bit mono PCM
      - sample rate: 8000/16000/32000/48000
      - frame size: 10/20/30 ms
    aggressiveness: 0 (least) .. 3 (most aggressive)
    """
    def __init__(self, sr: int = 16000, frame_ms: int = 20, aggressiveness: int = 2):
        if frame_ms not in (10, 20, 30):
            raise ValueError("frame_ms must be 10/20/30")
        if sr not in (8000, 16000, 32000, 48000):
            raise ValueError("sr must be one of 8000/16000/32000/48000")
        self.sr = sr
        self.frame_ms = frame_ms
        self.frame_bytes = int(sr * frame_ms / 1000) * 2  # int16 => 2 bytes
        try:
            import webrtcvad
        except ImportError as e:
            raise RuntimeError(
                "webrtcvad is not installed. Install with: python -m pip install webrtcvad"
            ) from e
        self.vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, pcm16: bytes, channels: int = 1) -> bool:
        mono = _first_channel_mono_pcm16(pcm16, channels)
        return self.vad.is_speech(mono, self.sr)
