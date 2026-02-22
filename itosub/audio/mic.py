from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import Iterator, Optional

from itosub.contracts import AudioChunk


class MicError(RuntimeError):
    pass


class SoundDeviceMicSource:
    """
    Live microphone source using the `sounddevice` package (PortAudio).
    Captures raw PCM16 chunks of fixed duration.
    """

    def __init__(
        self,
        *,
        chunk_seconds: float = 1.5,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None,
    ) -> None:
        if chunk_seconds <= 0:
            raise ValueError("chunk_seconds must be > 0")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be > 0")
        if channels not in (1, 2):
            raise ValueError("channels must be 1 or 2 (for now)")

        self.chunk_seconds = float(chunk_seconds)
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.device = device

    @staticmethod
    def list_devices() -> str:
        try:
            import sounddevice as sd
        except ImportError as e:
            raise MicError(
                "sounddevice is not installed. Install with: python -m pip install sounddevice"
            ) from e
        return str(sd.query_devices())

    @contextlib.contextmanager
    def _open_stream(self):
        try:
            import sounddevice as sd
        except ImportError as e:
            raise MicError(
                "sounddevice is not installed. Install with: python -m pip install sounddevice"
            ) from e

        try:
            stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
                blocksize=0,  # let PortAudio choose
            )
        except Exception as e:
            raise MicError(
                "Failed to open microphone stream. "
                "Try --list-devices and select a device id with --device."
            ) from e

        with stream:
            yield stream

    def chunks(self) -> Iterator[AudioChunk]:
        frames_per_chunk = int(round(self.chunk_seconds * self.sample_rate))
        if frames_per_chunk <= 0:
            frames_per_chunk = 1

        frames_seen = 0
        t0 = time.time()

        with self._open_stream() as stream:
            while True:
                data, overflowed = stream.read(frames_per_chunk)
                if overflowed:
                    # We keep going; overflow just means PortAudio dropped frames.
                    pass

                start_time = frames_seen / self.sample_rate
                duration = frames_per_chunk / self.sample_rate
                frames_seen += frames_per_chunk

                yield AudioChunk(
                    pcm16=bytes(data),
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    start_time=start_time,
                    duration=duration,
                )