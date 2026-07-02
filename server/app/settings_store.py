"""Generic Settings store (the Controller <-> Brain Settings contract).

Holds ONLY implementation-agnostic knobs (contracts.GenericSettings); the
Claude classifier's key/model/prompt live in its own private store
(roles/classifier/claude_config.py). One instance is cached in memory and
swapped on save, so admin edits take effect on the next frame with no restart.

Also owns the one-time migration from the pre-Phase-1 flat data/settings.json
(which mixed generic and classifier-private fields).
"""

import json
from pathlib import Path

from .contracts import GenericSettings

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SETTINGS_PATH = DATA_DIR / "settings.json"

# Fields that mark the old flat shape (classifier-private config mixed in).
_FLAT_MARKERS = {"api_key", "model", "system_prompt", "sample_interval_ms"}


def migrate_flat_settings(path: Path | None = None) -> bool:
    """Split a pre-Phase-1 flat settings.json into generic + classifier-private.

    Loss-proof ordering: the private file (holding the real API key) is written
    BEFORE settings.json is rewritten, so a crash mid-migration never loses the
    key. Idempotent — a generic-only file has none of the marker fields.
    Returns True if a migration ran.
    """
    path = path or SETTINGS_PATH
    if not path.exists():
        return False
    try:
        raw = json.loads(path.read_text())
    except Exception:
        return False  # corrupt file: leave it alone; load_settings falls back to defaults
    if not isinstance(raw, dict) or not (_FLAT_MARKERS & raw.keys()):
        return False

    from .roles.classifier import claude_config

    private = claude_config.ClaudeConfig(
        api_key=raw.get("api_key", ""),
        model=raw.get("model", claude_config.ClaudeConfig().model),
        system_prompt=raw.get("system_prompt", claude_config.DEFAULT_SYSTEM_PROMPT),
    )
    private_path = path.parent / claude_config.CONFIG_PATH.name
    if not private_path.exists():  # never clobber an existing private config
        claude_config.save_config(private, private_path)

    defaults = GenericSettings()
    generic = GenericSettings(
        sample_interval_s=raw.get("sample_interval_ms", 10000) / 1000.0,
        flip_threshold=raw.get("flip_threshold", defaults.flip_threshold),
        program=raw.get("program", defaults.program),
    )
    path.write_text(generic.model_dump_json(indent=2))
    return True


def load_settings(path: Path | None = None) -> GenericSettings:
    path = path or SETTINGS_PATH
    if not path.exists():
        settings = GenericSettings()
        save_settings(settings, path)
        return settings
    try:
        return GenericSettings.model_validate_json(path.read_text())
    except Exception:
        return GenericSettings()


def save_settings(settings: GenericSettings, path: Path | None = None) -> None:
    path = path or SETTINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(settings.model_dump_json(indent=2))


# --- Shared live instance ---------------------------------------------------------
_settings: GenericSettings | None = None


def get_settings() -> GenericSettings:
    global _settings
    if _settings is None:
        migrate_flat_settings()
        _settings = load_settings()
    return _settings


def set_settings(settings: GenericSettings) -> None:
    global _settings
    _settings = settings
