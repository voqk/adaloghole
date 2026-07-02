"""Load adaloghole.toml — the startup wiring config (architecture.md §7).

Static wiring only: which implementation fills each role, transports, and
per-implementation construction options. Runtime-tunable knobs live in the
generic Settings (settings_store.py); secrets live with the implementation
that needs them.
"""

import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "adaloghole.toml"

_DEFAULTS = {
    "roles": {
        "sensor": "webcam",
        "classifier": "claude",
        "brain": "local",
        "actuator": "none",
        "controller": "admin-web",
    },
    "transport": {"sensor": "localhost-http", "actuator": "in-process"},
    "server": {"host": "0.0.0.0", "port": 8000},
}


class Config:
    def __init__(self, raw: dict):
        self._raw = raw

    def role(self, role: str) -> str:
        """Implementation name chosen for a role, e.g. role('actuator') -> 'lirc'."""
        return self._raw.get("roles", {}).get(role, _DEFAULTS["roles"][role])

    def impl_options(self, role: str, name: str) -> dict:
        """Construction options for one implementation, e.g. [sensor.webcam]."""
        return dict(self._raw.get(role, {}).get(name, {}))

    def server(self) -> dict:
        return {**_DEFAULTS["server"], **self._raw.get("server", {})}

    def transport(self, seam: str) -> str:
        return self._raw.get("transport", {}).get(seam, _DEFAULTS["transport"].get(seam, "in-process"))


def load_config(path: Path | None = None) -> Config:
    path = path or CONFIG_PATH
    if not path.exists():
        return Config({})
    with path.open("rb") as f:
        return Config(tomllib.load(f))
