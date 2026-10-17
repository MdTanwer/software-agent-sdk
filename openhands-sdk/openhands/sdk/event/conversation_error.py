from pydantic import Field, model_validator
from rich.text import Text

from openhands.sdk.event.base import Event
from openhands.sdk.event.error_classification import (
    ErrorClassification,
    classify_error,
)
from openhands.sdk.event.error_origin import (
    grouping_key_for,
    validated_grouping_key,
    validated_origin,
)


class ConversationErrorEvent(Event):
    """
    Conversation-level failure that is NOT sent back to the LLM.

    This event is emitted by the conversation runtime when an unexpected
    exception bubbles up and prevents the run loop from continuing. It is
    intended for client applications (e.g., UIs) to present a top-level error
    state, and for orchestration to react. It is not an observation and it is
    not LLM-convertible.

    Differences from AgentErrorEvent:
    - Not tied to any tool_name/tool_call_id (AgentErrorEvent is a tool
      observation).
    - Typically source='environment' and the run loop moves to an ERROR state,
      while AgentErrorEvent has source='agent' and the conversation can
      continue.
    """

    code: str = Field(description="Code for the error - typically a type")
    detail: str = Field(description="Details about the error")
    classification: ErrorClassification | None = Field(
        default=None,
        description="Safe structured error semantics for API consumers.",
    )
    origin: str | None = Field(
        default=None,
        description=(
            "Sanitized module and function of the failure site. "
            "Omitted when no exception traceback is available."
        ),
    )
    grouping_key: str | None = Field(
        default=None,
        description=(
            "Stable key grouping the same module, function, and error code. "
            "Derived without line numbers, messages, paths, or secrets."
        ),
    )

    @model_validator(mode="after")
    def classify(self) -> "ConversationErrorEvent":
        if self.classification is None:
            object.__setattr__(
                self, "classification", classify_error(self.code, self.detail)
            )
        origin = validated_origin(self.origin)
        if origin != self.origin:
            object.__setattr__(self, "origin", origin)
        # The event code is the stable type. Recompute so every producer
        # groups the same way, and so a caller cannot store message text here.
        key = (
            grouping_key_for(origin, self.code)
            if origin is not None
            else validated_grouping_key(self.grouping_key)
        )
        if key != self.grouping_key:
            object.__setattr__(self, "grouping_key", key)
        return self

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation of this conversation error event."""
        content = Text()
        content.append("Conversation Error\n", style="bold")
        content.append("Code: ", style="bold")
        content.append(self.code)
        content.append("\n\nDetail:\n", style="bold")
        content.append(self.detail)
        return content
