from __future__ import annotations

import queue
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from itosub.ui.overlay_qt import SubtitleLine


class SubtitleBus:
    """
    Thread-safe handoff from worker thread -> UI thread.
    Worker puts SubtitleLine. UI polls (non-blocking).
    """
    def __init__(self, maxsize: int = 100):
        self.q: "queue.Queue[SubtitleLine]" = queue.Queue(maxsize=maxsize)

    def push(self, line: SubtitleLine) -> None:
        try:
            self.q.put_nowait(line)
        except queue.Full:
            # drop oldest to keep UI responsive
            try:
                _ = self.q.get_nowait()
            except queue.Empty:
                return
            try:
                self.q.put_nowait(line)
            except queue.Full:
                return

    def pop(self) -> Optional[SubtitleLine]:
        try:
            return self.q.get_nowait()
        except queue.Empty:
            return None
