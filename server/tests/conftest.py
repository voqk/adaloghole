"""Shared fixtures: an app wired with the static classifier + none actuator,
in-memory settings, and debug artifacts redirected off the real data/ dir."""

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def make_test_client(monkeypatch, script=None, label="commercial"):
    """Yield a TestClient over an app wired for tests (no network, no real data dir)."""
    from app import settings_store
    from app.config import Config
    from app.contracts import GenericSettings
    from app.main import create_app
    from app.roles.brain import core as brain_core

    # Known settings, no disk writes to the real data dir.
    monkeypatch.setattr(settings_store, "_settings", GenericSettings(flip_threshold=2))
    monkeypatch.setattr(settings_store, "save_settings", lambda s, path=None: None)
    monkeypatch.setattr(brain_core, "DATA_DIR", Path(tempfile.mkdtemp(prefix="adaloghole-test-")))

    cfg = Config({
        "roles": {"classifier": "static", "actuator": "none", "sensor": "none"},
        "classifier": {"static": {"label": label, "confidence": 0.9,
                                  "reason": "test stub", "script": script}},
    })
    app = create_app(cfg)
    with TestClient(app) as client:
        client.app = app
        yield client
