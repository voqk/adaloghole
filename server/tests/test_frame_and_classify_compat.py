"""The firmware-facing /classify contract: raw JPEG body in, flat JSON out.

The ESP32 (firmware/src/net.cpp) reads exactly two fields — `action` (string)
and `muted` (bool) — from a 200 response. Everything else can evolve, but a
break here strands the Phase 3 device.
"""

import pytest
from fastapi.testclient import TestClient

FAKE_JPEG = b"\xff\xd8\xff\xe0 not really a jpeg \xff\xd9"


@pytest.fixture()
def client(monkeypatch):
    try:  # post-refactor layout: static classifier is wired via conftest fixtures
        from tests.conftest import make_test_client
    except ImportError:
        make_test_client = None
    if make_test_client is not None:
        yield from make_test_client(monkeypatch)
        return

    # Pre-refactor layout: monkeypatch the classifier the device route calls.
    from app import routes_device
    from app.main import app

    def fake_classify(image_bytes, media_type="image/jpeg"):
        return {"label": "commercial", "confidence": 0.9, "reason": "test stub"}

    monkeypatch.setattr(routes_device, "classify_frame", fake_classify)
    # Fresh engine with a known threshold, independent of the user's settings.json.
    from app.decision import DecisionEngine

    monkeypatch.setattr(routes_device, "engine", DecisionEngine(flip_threshold=2))
    with TestClient(app) as c:
        yield c


def test_classify_returns_firmware_contract(client):
    resp = client.post(
        "/classify", content=FAKE_JPEG, headers={"Content-Type": "image/jpeg"}
    )
    assert resp.status_code == 200
    body = resp.json()
    # The two fields the device parses:
    assert body["action"] in {"mute", "unmute", "none"}
    assert isinstance(body["muted"], bool)
    # The human-facing extras:
    assert body["label"] in {"content", "program", "commercial", "unknown"}
    assert isinstance(body["confidence"], (int, float))
    assert isinstance(body["reason"], str)


def test_classify_debounces_across_requests(client):
    first = client.post("/classify", content=FAKE_JPEG).json()
    assert first["action"] == "none" and first["muted"] is False
    second = client.post("/classify", content=FAKE_JPEG).json()
    assert second["action"] == "mute" and second["muted"] is True


def test_classify_tolerates_non_image_content_type(client):
    resp = client.post(
        "/classify", content=FAKE_JPEG, headers={"Content-Type": "application/octet-stream"}
    )
    assert resp.status_code == 200
