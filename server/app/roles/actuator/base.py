"""Actuator role contract: Command -> Ack. Owns the IR code catalog.

An actuator declares its capabilities so the Brain can adapt; execute() must
never raise into the Brain — failures come back as Ack(ok=False, ...).
"""

from typing import Protocol, runtime_checkable

from ...contracts import Ack, Capabilities, Command


@runtime_checkable
class Actuator(Protocol):
    def execute(self, command: Command) -> Ack: ...

    def capabilities(self) -> Capabilities: ...
