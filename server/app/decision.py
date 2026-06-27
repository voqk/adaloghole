"""Debounce/hysteresis: raw frame labels -> a stable mute/unmute action.  [STUB]

This is the tunable core. A single odd frame must not flip the TV, so require N
consecutive same-label frames (flip_threshold) before changing state. "unknown"
holds the current state.
"""


class DecisionEngine:
    def __init__(self, flip_threshold: int = 2):
        # TODO: self.muted = False; self._pending_label = None; self._pending_count = 0
        raise NotImplementedError

    def feed(self, label: str) -> dict:
        """Feed one label; return {action: mute|unmute|none, muted: bool}."""
        raise NotImplementedError
