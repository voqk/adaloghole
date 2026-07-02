"""Private configuration for the Claude classifier implementation.

The API key, model id, and prompt template are implementation details of THIS
classifier — a local-model classifier has none of them — so they live here,
outside the shared Settings contract (architecture.md §2/§4). Persisted to
data/classifier_claude.json (gitignored), edited from the admin portal via the
AdminConfigurable protocol.
"""

from pathlib import Path

from pydantic import BaseModel

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
CONFIG_PATH = DATA_DIR / "classifier_claude.json"

# The system prompt is a template; the literal token {program} is substituted
# with the Context.program hint at classify time. Editable in the portal.
DEFAULT_SYSTEM_PROMPT = """You are a TV-watching assistant. You will be shown a single still frame captured from a television that is currently playing {program}.

Decide whether this frame is part of the actual program the viewer wants to watch, or a commercial / advertisement break.

Classify the frame as exactly one of:
- "program": the frame shows {program}, including its normal broadcast furniture (scoreboard, gameplay, in-studio coverage, commentary).
- "commercial": an advertisement, sponsor spot, channel promo, or anything that is not the program itself.
- "unknown": ambiguous, blank, a transition, or you genuinely cannot tell.

Return only the structured JSON verdict: a label, a confidence between 0 and 1, and a short reason."""


class ClaudeConfig(BaseModel):
    api_key: str = ""
    model: str = "claude-haiku-4-5"  # cheapest adequate vision model; portal-switchable
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


def load_config(path: Path | None = None) -> ClaudeConfig:
    path = path or CONFIG_PATH
    if not path.exists():
        return ClaudeConfig()
    try:
        return ClaudeConfig.model_validate_json(path.read_text())
    except Exception:
        # A hand-corrupted file shouldn't brick startup; fall back to defaults.
        return ClaudeConfig()


def save_config(config: ClaudeConfig, path: Path | None = None) -> None:
    path = path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))


# --- Shared live instance ---------------------------------------------------------
_config: ClaudeConfig | None = None


def get_config() -> ClaudeConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: ClaudeConfig) -> None:
    global _config
    _config = config
