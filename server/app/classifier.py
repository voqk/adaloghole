"""Call the Claude vision API on one frame.

Sends a single still frame to Claude with structured output (output_config.format),
NOT tool/function calling — we only need a typed JSON verdict back, not a callback
into our code.

This module is the single Anthropic touch-point. A future second backend (e.g. Gemini)
can be slotted in behind the same classify_frame() signature.
"""

import base64
import json

import anthropic

from .settings import get_settings

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


def classify_frame(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Return {label, confidence, reason} for a single frame.

    On any failure (no key, API error, bad response) returns label "unknown" with the
    cause in `reason` — "unknown" safely holds the current mute state downstream, and
    the reason surfaces in /admin/test and the device response.
    """
    s = get_settings()
    if not s.api_key:
        return {"label": "unknown", "confidence": 0.0, "reason": "no API key configured"}

    # .replace (not str.format) so stray braces in the user-edited prompt can't crash it.
    system = s.system_prompt.replace("{program}", s.program)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    try:
        client = anthropic.Anthropic(api_key=s.api_key)
        response = client.messages.create(
            model=s.model,
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
        return {
            "label": data["label"],
            "confidence": float(data["confidence"]),
            "reason": data["reason"],
        }
    except Exception as e:
        return {"label": "unknown", "confidence": 0.0, "reason": f"classifier error: {e}"}
