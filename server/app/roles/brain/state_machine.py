"""Decision state machine (architecture.md §6) — verdict stream -> stable A/V state.

Composes the proven DecisionEngine (the debounce core, unchanged) and adds:
  - mode:     auto (classifier drives) | override (user forced a state) |
              locked (hold current state, ignore the classifier)
  - av_state: unmuted | muted   ("music" is Phase 2 — soundbar source switch)

Commands are emitted on state CHANGE only, never every frame.

Concurrency: not thread-safe by design — feed()/apply_control() must only run
on the server event loop (the blocking classifier call happens in a threadpool
BEFORE the verdict is fed). Keep it that way.
"""

import time

from ...contracts import Command, Control, Verdict
from .debounce import DecisionEngine


class DecisionStateMachine:
    def __init__(self, flip_threshold: int = 2):
        self._engine = DecisionEngine(flip_threshold)
        self.mode: str = "auto"

    # --- Read-side ------------------------------------------------------------

    @property
    def muted(self) -> bool:
        return self._engine.muted

    @property
    def av_state(self) -> str:
        return "muted" if self._engine.muted else "unmuted"

    @property
    def flip_threshold(self) -> int:
        return self._engine.flip_threshold

    # --- Verdict path (Sensor frames) ------------------------------------------

    def feed(self, verdict: Verdict) -> Command | None:
        """Feed one verdict. Returns a Command iff the A/V state flipped.
        In override/locked mode the classifier is ignored (the caller still
        records the verdict for Status display)."""
        if self.mode != "auto":
            return None
        result = self._engine.feed(verdict.label)
        if result["action"] == "none":
            return None
        return self._command(result["action"], reason=f"classifier: {verdict.reason}")

    # --- Control path (the override knob) ---------------------------------------

    def apply_control(self, control: Control) -> Command | None:
        """Apply a Control. Returns a Command iff the A/V state flipped."""
        if control.override == "auto":
            self.mode = "locked" if control.lock else "auto"
            self._reset_pending()  # a stale half-counted run must not flip instantly
            return None

        self.mode = "override"
        want_muted = control.override == "force_mute"
        if want_muted == self._engine.muted:
            return None
        self._engine.muted = want_muted
        self._reset_pending()
        op = "mute" if want_muted else "unmute"
        return self._command(op, reason=f"user override: {control.override}")

    # --- Settings path ----------------------------------------------------------

    def set_flip_threshold(self, flip_threshold: int) -> None:
        """Apply a new threshold, preserving the current mute state."""
        muted = self._engine.muted
        self._engine = DecisionEngine(flip_threshold)
        self._engine.muted = muted

    # --- Internals ---------------------------------------------------------------

    def _reset_pending(self) -> None:
        self._engine._pending_label = None
        self._engine._pending_count = 0

    def _command(self, op: str, reason: str) -> Command:
        return Command(op=op, target="tv", code_ref=f"tv.{op}", reason=reason, ts=time.time())
