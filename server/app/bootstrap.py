"""Startup wiring: adaloghole.toml -> registry -> live role instances.

Imports the implementation modules (which self-register), instantiates the
configured implementation per role, and assembles the Brain. Adding a new
implementation = write a class + @register it + name it in the toml.
"""

import importlib
import logging
import threading
from types import SimpleNamespace

from . import registry
from .config import Config
from .roles.classifier.base import AdminConfigurable

logger = logging.getLogger("uvicorn.error")

# Implementation modules to import for registration. Missing optional deps
# (e.g. cv2 before `pip install -r requirements.txt`) disable that one
# implementation instead of bricking startup.
_IMPL_MODULES = (
    ".roles.classifier.claude",
    ".roles.classifier.static",
    ".roles.actuator.none",
    ".roles.actuator.lirc",
    ".roles.sensor.webcam",
)


def _import_implementations() -> None:
    for mod in _IMPL_MODULES:
        try:
            importlib.import_module(mod, __package__)
        except ImportError as e:
            logger.warning("implementation module %s unavailable: %s", mod, e)


def build_state(cfg: Config) -> SimpleNamespace:
    """Instantiate the configured implementation for each role and wire the Brain."""
    _import_implementations()
    from .roles.brain.core import Brain  # after registration imports

    classifier = registry.create(
        "classifier", cfg.role("classifier"), **cfg.impl_options("classifier", cfg.role("classifier"))
    )
    actuator = registry.create(
        "actuator", cfg.role("actuator"), **cfg.impl_options("actuator", cfg.role("actuator"))
    )
    brain = Brain(classifier, actuator)
    configurables = [c for c in (classifier, actuator) if isinstance(c, AdminConfigurable)]
    logger.info(
        "[wiring] classifier=%s actuator=%s sensor=%s",
        cfg.role("classifier"), cfg.role("actuator"), cfg.role("sensor"),
    )
    return SimpleNamespace(
        config=cfg, classifier=classifier, actuator=actuator, brain=brain,
        configurables=configurables,
    )


def start_sensor(cfg: Config, brain_url: str) -> tuple[threading.Thread, threading.Event] | None:
    """Start the configured Sensor as a daemon thread (if autostart is on).

    The sensor talks to the Brain over real localhost HTTP — the same wire
    binding a remote Phase 3 sensor uses. Returns (thread, stop_event), or None
    if no sensor should run in-process.
    """
    name = cfg.role("sensor")
    if name == "none":
        return None
    options = cfg.impl_options("sensor", name)
    if not options.pop("autostart", True):
        logger.info("[sensor] autostart off — run it yourself: python -m app.roles.sensor.%s", name)
        return None
    try:
        sensor = registry.create("sensor", name, brain_url=brain_url, **options)
    except ValueError as e:
        logger.warning("[sensor] not started: %s", e)
        return None
    stop = threading.Event()
    thread = threading.Thread(target=sensor.run, args=(stop,), name=f"sensor-{name}", daemon=True)
    thread.start()
    logger.info("[sensor] %s running (thread), posting to %s/frame", name, brain_url)
    return thread, stop
