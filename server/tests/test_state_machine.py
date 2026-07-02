"""Decision state machine (architecture.md §6): mode, av_state, Command emission."""

import pytest

from app.contracts import Control, Verdict
from app.roles.brain.state_machine import DecisionStateMachine


def v(label, reason="r"):
    return Verdict(label=label, confidence=0.9, reason=reason)


class TestAutoMode:
    def test_command_only_on_flip(self):
        m = DecisionStateMachine(flip_threshold=2)
        assert m.feed(v("commercial")) is None
        cmd = m.feed(v("commercial"))
        assert cmd is not None and cmd.op == "mute" and cmd.code_ref == "tv.mute"
        assert m.av_state == "muted"
        # No repeat command while the state holds.
        assert m.feed(v("commercial")) is None

    def test_content_unmutes_after_threshold(self):
        m = DecisionStateMachine(flip_threshold=2)
        m.feed(v("commercial")); m.feed(v("commercial"))
        assert m.feed(v("content")) is None
        cmd = m.feed(v("content"))
        assert cmd.op == "unmute" and m.av_state == "unmuted"

    def test_unknown_holds(self):
        m = DecisionStateMachine(flip_threshold=2)
        assert m.feed(v("unknown")) is None
        assert m.av_state == "unmuted"


class TestOverride:
    def test_force_mute_emits_command_and_ignores_classifier(self):
        m = DecisionStateMachine(flip_threshold=2)
        cmd = m.apply_control(Control(override="force_mute"))
        assert cmd.op == "mute" and m.mode == "override" and m.av_state == "muted"
        # Classifier now argues for unmute — ignored.
        for _ in range(5):
            assert m.feed(v("content")) is None
        assert m.av_state == "muted"

    def test_force_when_already_in_state_is_noop_command(self):
        m = DecisionStateMachine(flip_threshold=2)
        assert m.apply_control(Control(override="force_unmute")) is None
        assert m.mode == "override"

    def test_return_to_auto_resets_pending(self):
        m = DecisionStateMachine(flip_threshold=2)
        m.feed(v("commercial"))  # pending count 1
        m.apply_control(Control(override="force_unmute"))
        m.apply_control(Control(override="auto"))
        assert m.mode == "auto"
        # The stale pending frame must not count toward a flip.
        assert m.feed(v("commercial")) is None
        assert m.feed(v("commercial")).op == "mute"


class TestLocked:
    def test_lock_holds_current_state(self):
        m = DecisionStateMachine(flip_threshold=1)
        m.feed(v("commercial"))
        assert m.av_state == "muted"
        assert m.apply_control(Control(override="auto", lock=True)) is None
        assert m.mode == "locked"
        assert m.feed(v("content")) is None
        assert m.av_state == "muted"

    def test_unlock_returns_to_auto(self):
        m = DecisionStateMachine(flip_threshold=1)
        m.apply_control(Control(override="auto", lock=True))
        m.apply_control(Control(override="auto"))
        assert m.mode == "auto"
        assert m.feed(v("commercial")).op == "mute"


class TestThreshold:
    def test_set_flip_threshold_preserves_state(self):
        m = DecisionStateMachine(flip_threshold=1)
        m.feed(v("commercial"))
        m.set_flip_threshold(3)
        assert m.av_state == "muted" and m.flip_threshold == 3
        m.feed(v("content")); m.feed(v("content"))
        assert m.av_state == "muted"  # 2 < 3
        assert m.feed(v("content")).op == "unmute"


class TestOverHttp:
    """The Control/Status seam end-to-end through the wired app."""

    @pytest.fixture()
    def client(self, monkeypatch):
        from tests.conftest import make_test_client
        yield from make_test_client(monkeypatch, label="content")

    def test_control_and_status_roundtrip(self, client):
        assert client.get("/status").json()["av_state"] == "unmuted"
        s = client.post("/control", json={"override": "force_mute"}).json()
        assert s["mode"] == "override" and s["av_state"] == "muted"
        # Content frames arrive but are ignored under override.
        client.post("/frame", content=b"x", headers={"Content-Type": "image/jpeg"})
        assert client.get("/status").json()["av_state"] == "muted"
        s = client.post("/control", json={"override": "auto"}).json()
        assert s["mode"] == "auto"

    def test_settings_roundtrip(self, client):
        s = client.get("/settings").json()
        assert s["flip_threshold"] == 2
        s["flip_threshold"] = 4
        updated = client.put("/settings", json=s).json()
        assert updated["flip_threshold"] == 4

    def test_capabilities(self, client):
        caps = client.get("/capabilities").json()
        assert caps["can_mute"] is True and "tv" in caps["targets"]

    def test_frame_returns_verdict_status_command(self, client):
        r = client.post("/frame", content=b"x", headers={"Content-Type": "image/jpeg"}).json()
        assert r["verdict"]["label"] == "content"
        assert r["status"]["av_state"] == "unmuted"
        assert r["command"] is None  # already unmuted; no flip
