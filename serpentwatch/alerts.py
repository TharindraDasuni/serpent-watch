"""Decides when a run of detections is worth an alert."""
from __future__ import annotations


class AlertGate:
    """Fires once per sighting: needs N consecutive hits, then stays quiet for a cooldown."""

    def __init__(self, confirm_frames: int, cooldown_seconds: float):
        self._confirm_frames = confirm_frames
        self._cooldown = cooldown_seconds
        self._streak = 0
        self._last_fired = float("-inf")

    def update(self, detected: bool, now: float) -> bool:
        if not detected:
            self._streak = 0
            return False
        self._streak += 1
        if self._streak < self._confirm_frames:
            return False
        if now - self._last_fired < self._cooldown:
            return False
        self._last_fired = now
        return True
