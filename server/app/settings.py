"""Server configuration, editable from the admin portal.  [STUB]

Holds the user's Anthropic key, model, program description, the system prompt, and
the decision thresholds. Persisted to data/settings.json (gitignored) so a user can
enter their own key and tune the prompt without touching code.
"""

# TODO: pydantic BaseModel with fields:
#   api_key: str
#   model: str = "claude-opus-4-8"   # or claude-sonnet-4-6 / claude-haiku-4-5
#   program: str = "a live sports broadcast such as a baseball game"
#   system_prompt: str               # template; {program} interpolated
#   flip_threshold: int = 2
#   sample_interval_ms: int = 10000  # advertised to the device
# TODO: load() / save() against data/settings.json


def load_settings():
    """Load settings from data/settings.json (creating defaults on first run)."""
    raise NotImplementedError


def save_settings(settings) -> None:
    raise NotImplementedError
