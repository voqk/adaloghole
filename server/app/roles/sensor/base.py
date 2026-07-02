"""Sensor role contract: grab frames on a cadence and submit them to the Brain.

The Sensor OWNS the cadence (architecture.md §3) — in the final hardware the
sensor device is what runs the timer. It talks to the Brain over the wire
binding (POST /frame) even when it happens to run in the same process, because
this is the first seam to go remote (Phase 3 ESP32).
"""

import threading
from typing import Protocol


class Sensor(Protocol):
    def run(self, stop: threading.Event) -> None:
        """Blocking capture loop; return promptly once `stop` is set."""
        ...
