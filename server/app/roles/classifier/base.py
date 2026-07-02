"""Classifier role contract: Frame (+Context) -> Verdict. Pure inference.

A classifier knows nothing about IR, muting, or debounce. Its own configuration
(prompt, model id, API key, weights path) is private to the implementation and
never appears in the shared contract (architecture.md §3).
"""

from abc import ABC, abstractmethod
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from ...contracts import Context, Verdict


class Classifier(ABC):
    @abstractmethod
    def classify(self, image: bytes, media_type: str, context: Context) -> Verdict:
        """Classify one frame. Must never raise: on any internal failure return
        label "unknown" with the cause in `reason` — unknown safely holds the
        current mute state downstream."""


class FieldSpec(BaseModel):
    """One admin-portal form field for implementation-private config."""

    label: str
    value: str = ""
    secret: bool = False  # never echo the stored value back into the form
    widget: Literal["text", "textarea", "select"] = "text"
    options: list[str] = []
    hint: str = ""


@runtime_checkable
class AdminConfigurable(Protocol):
    """Optional protocol: a role implementation whose private config is editable
    from the admin portal. The portal renders one generic fieldset per
    configurable implementation — private config never enters the shared
    Settings contract."""

    admin_id: str  # slug used to prefix form field names, e.g. "classifier_claude"
    admin_title: str

    def admin_fields(self) -> dict[str, FieldSpec]: ...

    def apply_admin_fields(self, form: dict[str, str]) -> None: ...
