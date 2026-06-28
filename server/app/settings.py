"""Server configuration, editable from the admin portal.

Holds the user's Anthropic key, model, program description, the system prompt, and
the decision thresholds. Persisted to data/settings.json (gitignored) so a user can
enter their own key and tune the prompt without touching code.

One Settings instance is cached in memory and swapped on save (see set_settings), so
admin edits take effect on the next frame with no restart.
"""

from pathlib import Path

from pydantic import BaseModel

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SETTINGS_PATH = DATA_DIR / "settings.json"

# The system prompt is a template; the literal token {program} is substituted with the
# user's program description (settings.program) at classify time. Editable in the portal.
DEFAULT_SYSTEM_PROMPT = """You are a TV-watching assistant. You will be shown a single still frame captured from a television that is currently playing {program}.

Decide whether this frame is part of the actual program the viewer wants to watch, or a commercial / advertisement break.

Classify the frame as exactly one of:
- "program": the frame shows {program}, including its normal broadcast furniture (scoreboard, gameplay, in-studio coverage, commentary).
- "commercial": an advertisement, sponsor spot, channel promo, or anything that is not the program itself.
- "unknown": ambiguous, blank, a transition, or you genuinely cannot tell.

Return only the structured JSON verdict: a label, a confidence between 0 and 1, and a short reason."""


class Settings(BaseModel):
    api_key: str = ""
    model: str = "claude-haiku-4-5"  # or claude-sonnet-4-6 / claude-opus-4-8
    program: str = "a live sports broadcast such as a baseball game"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT  # template; {program} interpolated
    flip_threshold: int = 2
    sample_interval_ms: int = 10000  # advertised to the device


def load_settings() -> Settings:
    """Load settings from data/settings.json (creating defaults on first run)."""
    if not SETTINGS_PATH.exists():
        settings = Settings()
        save_settings(settings)
        return settings
    try:
        return Settings.model_validate_json(SETTINGS_PATH.read_text())
    except Exception:
        # A hand-corrupted file shouldn't brick startup; fall back to defaults.
        return Settings()


def save_settings(settings: Settings) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(settings.model_dump_json(indent=2))


# --- Shared live instance ---------------------------------------------------------
# classify_frame() reads get_settings() on every call; the admin POST swaps the cached
# instance via set_settings(), so edits are live without a restart (single process).

_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def set_settings(settings: Settings) -> None:
    global _settings
    _settings = settings
