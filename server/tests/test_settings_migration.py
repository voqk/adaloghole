"""Splitting the pre-Phase-1 flat settings.json must never lose the API key."""

import json

from app.contracts import GenericSettings
from app.roles.classifier import claude_config
from app.settings_store import load_settings, migrate_flat_settings, save_settings

FLAT = {
    "api_key": "sk-ant-api03-REAL-KEY",
    "model": "claude-haiku-4-5",
    "program": "a live sports broadcast such as a soccer match",
    "system_prompt": "Watch {program}.\r\nBe careful.",
    "flip_threshold": 3,
    "sample_interval_ms": 5000,
}


def write_flat(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps(FLAT))
    return p


def test_migration_splits_private_and_generic(tmp_path):
    p = write_flat(tmp_path)
    assert migrate_flat_settings(p) is True

    private = claude_config.load_config(tmp_path / "classifier_claude.json")
    assert private.api_key == FLAT["api_key"]
    assert private.model == FLAT["model"]
    assert private.system_prompt == FLAT["system_prompt"]  # CRLF preserved as-is

    generic = load_settings(p)
    assert generic.sample_interval_s == 5.0  # ms -> s
    assert generic.flip_threshold == 3
    assert generic.program == FLAT["program"]

    # No private field survives in the generic file.
    raw = json.loads(p.read_text())
    assert not {"api_key", "model", "system_prompt"} & raw.keys()


def test_migration_is_idempotent(tmp_path):
    p = write_flat(tmp_path)
    assert migrate_flat_settings(p) is True
    assert migrate_flat_settings(p) is False  # second run: nothing to do

    private = claude_config.load_config(tmp_path / "classifier_claude.json")
    assert private.api_key == FLAT["api_key"]


def test_migration_never_clobbers_existing_private_config(tmp_path):
    existing = claude_config.ClaudeConfig(api_key="sk-ant-KEEP-ME")
    claude_config.save_config(existing, tmp_path / "classifier_claude.json")
    write_flat(tmp_path)
    migrate_flat_settings(tmp_path / "settings.json")
    private = claude_config.load_config(tmp_path / "classifier_claude.json")
    assert private.api_key == "sk-ant-KEEP-ME"


def test_corrupt_file_left_alone(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{not json")
    assert migrate_flat_settings(p) is False
    assert p.read_text() == "{not json"
    assert load_settings(p) == GenericSettings()  # falls back to defaults


def test_missing_file_creates_defaults(tmp_path):
    p = tmp_path / "settings.json"
    assert migrate_flat_settings(p) is False
    s = load_settings(p)
    assert s == GenericSettings()
    assert p.exists()


def test_generic_roundtrip(tmp_path):
    p = tmp_path / "settings.json"
    s = GenericSettings(sample_interval_s=2.5, flip_threshold=4, program="hockey")
    save_settings(s, p)
    assert load_settings(p) == s
