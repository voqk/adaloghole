"""LIRC actuator — fires IR via `irsend` (USB-UIRT or any LIRC-supported blaster).

Owns the IR code catalog: the [actuator.lirc.codes] table in adaloghole.toml
maps Command code_refs ("tv.mute") to LIRC key names ("KEY_MUTE") learned with
irrecord — see docs/lirc-setup.md for the one-time hardware setup.

Failure policy: execute() never raises into the Brain. A missing irsend binary,
unknown code_ref, timeout, or non-zero exit comes back as Ack(ok=False, ...) —
the loop keeps running and the failure is visible in the logs and Status.
"""

import logging
import shutil
import subprocess

from ...contracts import Ack, Capabilities, Command
from ...registry import register

logger = logging.getLogger("uvicorn.error")

_IRSEND_TIMEOUT_S = 2.0  # irsend returns near-instantly; anything longer is wedged


@register("actuator", "lirc")
class LircActuator:
    def __init__(self, remote: str = "tv", codes: dict[str, str] | None = None):
        self.remote = remote
        self.codes = dict(codes or {})
        self.irsend = shutil.which("irsend")
        if self.irsend is None:
            logger.warning(
                "[actuator:lirc] irsend not found — install LIRC and set up the "
                "USB-UIRT first (docs/lirc-setup.md). Commands will fail gracefully."
            )

    def execute(self, command: Command) -> Ack:
        if command.op == "noop":
            return Ack(ok=True, executed=False, detail="noop")
        if self.irsend is None:
            return Ack(ok=False, executed=False, detail="irsend not installed (see docs/lirc-setup.md)")
        key = self.codes.get(command.code_ref)
        if key is None:
            return Ack(
                ok=False, executed=False,
                detail=f"no IR code for {command.code_ref!r}; known: {sorted(self.codes)}",
            )
        argv = [self.irsend, "SEND_ONCE", self.remote, key]
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=_IRSEND_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return Ack(ok=False, executed=False, detail=f"irsend timed out after {_IRSEND_TIMEOUT_S}s")
        except OSError as e:
            return Ack(ok=False, executed=False, detail=f"irsend failed to start: {e}")
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
            return Ack(ok=False, executed=False, detail=f"irsend error: {detail}")
        logger.info("[actuator:lirc] fired %s -> %s %s", command.op, self.remote, key)
        return Ack(ok=True, executed=True, detail=f"irsend SEND_ONCE {self.remote} {key}")

    def capabilities(self) -> Capabilities:
        return Capabilities(
            can_mute="tv.mute" in self.codes,
            can_switch_source=any(ref.startswith("soundbar.") for ref in self.codes),
            targets=sorted({ref.split(".", 1)[0] for ref in self.codes}),
        )
