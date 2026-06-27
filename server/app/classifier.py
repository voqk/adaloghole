"""Call the Claude vision API on one frame.  [STUB]

Plan:
  client = anthropic.Anthropic(api_key=settings.api_key)
  client.messages.create(
      model=settings.model,
      max_tokens=300,
      system=settings.system_prompt,
      output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
      messages=[{"role": "user", "content": [<base64 image>, {"type": "text", ...}]}],
  )
  SCHEMA: { label: program|commercial|unknown, confidence: number, reason: string }

Note: structured output (output_config.format), NOT tool/function calling — we only
need the model to return a typed JSON verdict, not to call back into our code.
"""


def classify_frame(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Return {label, confidence, reason} for a single frame."""
    raise NotImplementedError
