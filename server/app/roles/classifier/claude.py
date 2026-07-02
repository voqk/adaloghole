"""Claude classifier — the reference hosted-LLM Classifier implementation.

Sends a single still frame to Claude with structured output
(output_config.format), NOT tool/function calling — we only need a typed JSON
verdict back, not a callback into our code. This module is the single
Anthropic touch-point.

Vocabulary note: the model-facing enum uses "program" (it reads naturally next
to the {program} prompt token); the canonical wire label is "content"
(architecture.md §4). The mapping happens here, privately.
"""

import base64
import json

import anthropic

from ...contracts import Context, Verdict
from ...registry import register
from . import claude_config
from .base import AdminConfigurable, Classifier, FieldSpec

# Structured-output schema: the typed JSON verdict we want back.
SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["program", "commercial", "unknown"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["label", "confidence", "reason"],
    "additionalProperties": False,
}

_MODEL_OPTIONS = [
    "claude-haiku-4-5",   # cheapest, adequate for this frequent simple classification
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-opus-4-8",
]

_LABEL_MAP = {"program": "content", "commercial": "commercial", "unknown": "unknown"}


@register("classifier", "claude")
class ClaudeClassifier(Classifier, AdminConfigurable):
    admin_id = "classifier_claude"
    admin_title = "Claude classifier"

    def classify(self, image: bytes, media_type: str, context: Context) -> Verdict:
        cfg = claude_config.get_config()
        if not cfg.api_key:
            return Verdict(label="unknown", confidence=0.0, reason="no API key configured")

        # .replace (not str.format) so stray braces in the user-edited prompt can't crash it.
        system = cfg.system_prompt.replace("{program}", context.program)
        b64 = base64.standard_b64encode(image).decode("ascii")

        try:
            client = anthropic.Anthropic(api_key=cfg.api_key)
            response = client.messages.create(
                model=cfg.model,
                max_tokens=300,
                system=system,
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "base64", "media_type": media_type, "data": b64},
                            },
                            {"type": "text", "text": "Classify this TV frame."},
                        ],
                    }
                ],
            )
            # output_config.format guarantees the first text block is JSON matching SCHEMA.
            text = next(block.text for block in response.content if block.type == "text")
            data = json.loads(text)
            return Verdict(
                label=_LABEL_MAP[data["label"]],
                confidence=float(data["confidence"]),
                reason=data["reason"],
            )
        except Exception as e:
            return Verdict(label="unknown", confidence=0.0, reason=f"classifier error: {e}")

    # --- AdminConfigurable -----------------------------------------------------

    def admin_fields(self) -> dict[str, FieldSpec]:
        cfg = claude_config.get_config()
        return {
            "api_key": FieldSpec(
                label="Anthropic API key",
                secret=True,
                hint="stored server-side; leave blank to keep the current key",
            ),
            "model": FieldSpec(
                label="Model",
                value=cfg.model,
                widget="select",
                options=_MODEL_OPTIONS,
                hint="haiku is much cheaper and adequate for this classification",
            ),
            "system_prompt": FieldSpec(
                label="System prompt template",
                value=cfg.system_prompt,
                widget="textarea",
                hint="the literal token {program} is replaced with the program description",
            ),
        }

    def apply_admin_fields(self, form: dict[str, str]) -> None:
        cfg = claude_config.get_config()
        new = claude_config.ClaudeConfig(
            api_key=form.get("api_key") or cfg.api_key,  # blank keeps the existing key
            model=form.get("model", cfg.model),
            system_prompt=form.get("system_prompt", cfg.system_prompt),
        )
        claude_config.save_config(new)
        claude_config.set_config(new)
