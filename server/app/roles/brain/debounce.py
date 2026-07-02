"""Debounce/hysteresis: raw frame labels -> a stable mute/unmute action.

This is the tunable core. A single odd frame must not flip the TV, so require N
consecutive same-label frames (flip_threshold) before changing state. "unknown"
holds the current state.

One shared instance per Brain (single TV), wrapped by DecisionStateMachine.
"""


class DecisionEngine:
    def __init__(self, flip_threshold: int = 2):
        self.flip_threshold = flip_threshold
        self.muted = False
        self._pending_label: str | None = None
        self._pending_count = 0

    def feed(self, label: str) -> dict:
        """Feed one label; return {action: mute|unmute|none, muted: bool}."""
        # "unknown" tells us nothing — hold the current state.
        if label == "unknown":
            return {"action": "none", "muted": self.muted}

        # Map label -> the mute state it argues for.
        desired = label == "commercial"

        # Already in the right state: nothing to do, and any pending flip is stale.
        if desired == self.muted:
            self._pending_label = None
            self._pending_count = 0
            return {"action": "none", "muted": self.muted}

        # The state wants to flip. Count consecutive frames agreeing on the new label;
        # a single contrary frame resets the count, so it can never flip on its own.
        if label == self._pending_label:
            self._pending_count += 1
        else:
            self._pending_label = label
            self._pending_count = 1

        if self._pending_count >= self.flip_threshold:
            self.muted = desired
            self._pending_label = None
            self._pending_count = 0
            return {"action": "mute" if self.muted else "unmute", "muted": self.muted}

        # Still debouncing — no action yet.
        return {"action": "none", "muted": self.muted}
