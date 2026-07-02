"""The Brain — the hub and only stateful role (architecture.md §3).

Receives frames, calls the Classifier, feeds verdicts through the decision
state machine, holds the authoritative A/V state and the generic Settings,
emits Commands to the Actuator, and serves Status/Control to the Controller.
One Brain per TV.
"""

import json
import logging
import time
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from ... import settings_store
from ...contracts import (
    Capabilities,
    Command,
    Context,
    Control,
    FrameMeta,
    FrameResponse,
    GenericSettings,
    Status,
)
from ..actuator.base import Actuator
from ..classifier.base import Classifier
from .state_machine import DecisionStateMachine

logger = logging.getLogger("uvicorn.error")

# Debug artifacts for camera/prompt tuning: the most recent frame + its verdict,
# written best-effort to the gitignored data/ dir. Overwritten each frame.
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


class Brain:
    def __init__(self, classifier: Classifier, actuator: Actuator):
        self._classifier = classifier
        self._actuator = actuator
        self._machine = DecisionStateMachine(settings_store.get_settings().flip_threshold)
        self._started = time.monotonic()
        self._last_verdict = None
        self._last_source: str | None = None

    # --- Frame intake (the /frame seam, née /classify) --------------------------

    async def handle_frame(self, image: bytes, media_type: str, meta: FrameMeta) -> FrameResponse:
        """Classify one frame and run the decision state machine.

        The blocking classifier call runs in a threadpool; the state-machine
        update runs back on the event loop, which is what keeps the (lock-free)
        machine safe under concurrent frame posts.
        """
        context = Context(program=settings_store.get_settings().program)
        verdict = await run_in_threadpool(self._classifier.classify, image, media_type, context)
        command = self._machine.feed(verdict)
        self._last_verdict = verdict
        self._last_source = meta.source_id
        if command is not None:
            ack = self._actuator.execute(command)
            if not ack.ok:
                logger.warning("[brain] actuator failed %s: %s", command.op, ack.detail)
        response = FrameResponse(verdict=verdict, status=self.status(), command=command)
        self._save_debug(image, verdict, command)
        return response

    # --- Controller-facing ---------------------------------------------------------

    def control(self, control: Control) -> Status:
        command = self._machine.apply_control(control)
        if command is not None:
            ack = self._actuator.execute(command)
            if not ack.ok:
                logger.warning("[brain] actuator failed %s: %s", command.op, ack.detail)
        return self.status()

    def status(self) -> Status:
        v = self._last_verdict
        return Status(
            mode=self._machine.mode,
            av_state=self._machine.av_state,
            last_label=v.label if v else None,
            last_confidence=v.confidence if v else None,
            last_reason=v.reason if v else None,
            source_id=self._last_source,
            uptime_s=round(time.monotonic() - self._started, 1),
        )

    def capabilities(self) -> Capabilities:
        return self._actuator.capabilities()

    def get_settings(self) -> GenericSettings:
        return settings_store.get_settings()

    def put_settings(self, new: GenericSettings) -> GenericSettings:
        current = settings_store.get_settings()
        settings_store.save_settings(new)
        settings_store.set_settings(new)
        if new.flip_threshold != current.flip_threshold:
            self._machine.set_flip_threshold(new.flip_threshold)  # preserves mute state
        return new

    # --- Internals -------------------------------------------------------------------

    def _save_debug(self, image: bytes, verdict, command: Command | None) -> None:
        """Persist the last frame + verdict for tuning. Never raises into the request."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / "last_frame.jpg").write_bytes(image)
            record = {
                "verdict": verdict.model_dump(),
                "action": command.op if command else "none",
                "av_state": self._machine.av_state,
                "mode": self._machine.mode,
            }
            (DATA_DIR / "last_verdict.json").write_text(json.dumps(record, indent=2))
            logger.info(
                "[frame] %dB -> label=%s conf=%.2f action=%s av_state=%s :: %s",
                len(image), verdict.label, verdict.confidence,
                record["action"], record["av_state"], verdict.reason,
            )
        except Exception:
            pass  # tuning aid only — a disk/log hiccup must not break classification
