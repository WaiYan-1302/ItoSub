from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class RuntimeStateTracker:
    state: RuntimeState = RuntimeState.STOPPED
    last_error: str | None = None

    def set_starting(self) -> None:
        self.state = RuntimeState.STARTING
        self.last_error = None

    def set_running(self) -> None:
        self.state = RuntimeState.RUNNING

    def set_paused(self) -> None:
        if self.state in (RuntimeState.RUNNING, RuntimeState.STARTING):
            self.state = RuntimeState.PAUSED

    def set_resumed(self) -> None:
        if self.state == RuntimeState.PAUSED:
            self.state = RuntimeState.RUNNING

    def set_stopped(self) -> None:
        self.state = RuntimeState.STOPPED

    def set_error(self, detail: str) -> None:
        self.state = RuntimeState.ERROR
        self.last_error = detail

