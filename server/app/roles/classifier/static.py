"""Static classifier — a deterministic stand-in for tests and offline dev.

Returns a fixed verdict, or cycles through a scripted sequence of labels.
Selected with classifier = "static" in adaloghole.toml; no network, no key.
"""

from ...contracts import Context, Verdict
from ...registry import register
from .base import Classifier


@register("classifier", "static")
class StaticClassifier(Classifier):
    def __init__(self, label: str = "content", confidence: float = 1.0,
                 reason: str = "static classifier", script: list[str] | None = None):
        self.label = label
        self.confidence = confidence
        self.reason = reason
        self.script = script  # optional label sequence, cycled
        self._i = 0

    def classify(self, image: bytes, media_type: str, context: Context) -> Verdict:
        label = self.label
        if self.script:
            label = self.script[self._i % len(self.script)]
            self._i += 1
        return Verdict(label=label, confidence=self.confidence, reason=self.reason)
