"""Actuator implementations: log-only default + LIRC shell-out (subprocess mocked)."""

import subprocess
import time

import pytest

from app.contracts import Command
from app.roles.actuator.lirc import LircActuator
from app.roles.actuator.none import NoneActuator

CODES = {"tv.mute": "KEY_MUTE", "tv.unmute": "KEY_MUTE"}


def cmd(op="mute", code_ref="tv.mute"):
    return Command(op=op, target="tv", code_ref=code_ref, reason="test", ts=time.time())


class TestNoneActuator:
    def test_acks_without_executing(self):
        ack = NoneActuator().execute(cmd())
        assert ack.ok is True and ack.executed is False

    def test_capabilities_claim_mute(self):
        caps = NoneActuator().capabilities()
        assert caps.can_mute is True and caps.targets == ["tv"]


class TestLircActuator:
    @pytest.fixture()
    def actuator(self, monkeypatch):
        monkeypatch.setattr("app.roles.actuator.lirc.shutil.which", lambda _: "/usr/bin/irsend")
        return LircActuator(remote="tv", codes=CODES)

    def test_fires_irsend_send_once(self, actuator, monkeypatch):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        ack = actuator.execute(cmd("mute", "tv.mute"))
        assert ack.ok is True and ack.executed is True
        assert calls == [["/usr/bin/irsend", "SEND_ONCE", "tv", "KEY_MUTE"]]

    def test_nonzero_exit_is_failed_ack_not_exception(self, actuator, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda argv, **kw: subprocess.CompletedProcess(argv, 1, stdout="", stderr="hardware does not exist"),
        )
        ack = actuator.execute(cmd())
        assert ack.ok is False and ack.executed is False
        assert "hardware does not exist" in ack.detail

    def test_timeout_is_failed_ack(self, actuator, monkeypatch):
        def raise_timeout(argv, **kw):
            raise subprocess.TimeoutExpired(argv, 2.0)

        monkeypatch.setattr(subprocess, "run", raise_timeout)
        ack = actuator.execute(cmd())
        assert ack.ok is False and "timed out" in ack.detail

    def test_unknown_code_ref(self, actuator):
        ack = actuator.execute(cmd("mute", "projector.mute"))
        assert ack.ok is False and "projector.mute" in ack.detail

    def test_missing_irsend_binary(self, monkeypatch):
        monkeypatch.setattr("app.roles.actuator.lirc.shutil.which", lambda _: None)
        actuator = LircActuator(remote="tv", codes=CODES)
        ack = actuator.execute(cmd())
        assert ack.ok is False and "not installed" in ack.detail

    def test_capabilities_from_code_catalog(self, actuator):
        caps = actuator.capabilities()
        assert caps.can_mute is True
        assert caps.can_switch_source is False
        assert caps.targets == ["tv"]

    def test_noop_command(self, actuator):
        ack = actuator.execute(cmd("noop", ""))
        assert ack.ok is True and ack.executed is False
