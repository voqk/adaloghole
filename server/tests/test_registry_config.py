"""Registry + config-loader wiring (architecture.md §7)."""

import textwrap

import pytest

from app import registry
from app.config import load_config


class TestRegistry:
    def test_register_and_create(self):
        @registry.register("actuator", "_test_fake")
        class FakeActuator:
            def __init__(self, remote="tv"):
                self.remote = remote

        inst = registry.create("actuator", "_test_fake", remote="soundbar")
        assert isinstance(inst, FakeActuator)
        assert inst.remote == "soundbar"

    def test_unknown_name_lists_registered_options(self):
        with pytest.raises(ValueError, match="no actuator implementation named 'bogus'"):
            registry.create("actuator", "bogus")

    def test_unknown_role_rejected(self):
        with pytest.raises(ValueError, match="unknown role"):
            registry.create("flux-capacitor", "x")


class TestConfig:
    def test_repo_toml_parses_with_expected_wiring(self):
        cfg = load_config()  # the committed adaloghole.toml
        assert cfg.role("sensor") == "webcam"
        assert cfg.role("classifier") == "claude"
        assert cfg.role("actuator") in {"none", "lirc"}
        assert cfg.transport("sensor") == "localhost-http"
        assert isinstance(cfg.server()["port"], int)
        webcam = cfg.impl_options("sensor", "webcam")
        assert "device" in webcam and "autostart" in webcam

    def test_lirc_code_catalog_present(self):
        cfg = load_config()
        codes = cfg.impl_options("actuator", "lirc")["codes"]
        assert "tv.mute" in codes and "tv.unmute" in codes

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        cfg = load_config(tmp_path / "nope.toml")
        assert cfg.role("actuator") == "none"
        assert cfg.server()["port"] == 8000
        assert cfg.impl_options("sensor", "webcam") == {}

    def test_custom_toml(self, tmp_path):
        p = tmp_path / "adaloghole.toml"
        p.write_text(textwrap.dedent("""
            [roles]
            actuator = "lirc"
            [actuator.lirc]
            remote = "livingroom"
        """))
        cfg = load_config(p)
        assert cfg.role("actuator") == "lirc"
        assert cfg.impl_options("actuator", "lirc")["remote"] == "livingroom"
        assert cfg.role("sensor") == "webcam"  # unspecified -> default
