"""Log-only actuator — the day-one default while no IR hardware is attached.

Logs every Command it receives and acknowledges without executing, so the whole
see->decide loop runs today; swap actuator = "lirc" in adaloghole.toml once the
USB-UIRT is set up (docs/lirc-setup.md).
"""

import logging

from ...contracts import Ack, Capabilities, Command
from ...registry import register

logger = logging.getLogger("uvicorn.error")


@register("actuator", "none")
class NoneActuator:
    def execute(self, command: Command) -> Ack:
        logger.info(
            "[actuator:none] would fire %s (%s) — %s",
            command.op, command.code_ref, command.reason,
        )
        return Ack(ok=True, executed=False, detail="log-only actuator: no IR hardware")

    def capabilities(self) -> Capabilities:
        # Claims mute so the Brain exercises the full Command path.
        return Capabilities(can_mute=True, can_switch_source=False, targets=["tv"])
