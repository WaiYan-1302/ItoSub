from __future__ import annotations

from itosub.app.state import RuntimeState, RuntimeStateTracker


def test_state_tracker_happy_path() -> None:
    tracker = RuntimeStateTracker()
    assert tracker.state == RuntimeState.STOPPED
    assert tracker.last_error is None

    tracker.set_starting()
    assert tracker.state == RuntimeState.STARTING

    tracker.set_running()
    assert tracker.state == RuntimeState.RUNNING

    tracker.set_paused()
    assert tracker.state == RuntimeState.PAUSED

    tracker.set_resumed()
    assert tracker.state == RuntimeState.RUNNING

    tracker.set_stopped()
    assert tracker.state == RuntimeState.STOPPED


def test_state_tracker_error_clears_on_restart() -> None:
    tracker = RuntimeStateTracker()
    tracker.set_error("boom")
    assert tracker.state == RuntimeState.ERROR
    assert tracker.last_error == "boom"

    tracker.set_starting()
    assert tracker.state == RuntimeState.STARTING
    assert tracker.last_error is None

