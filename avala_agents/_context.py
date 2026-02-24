"""Context objects passed to agent event handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from avala_agents._agent import TaskAgent


@dataclass
class ResultContext:
    """
    Context passed to handlers registered for result events.

    Provides access to the annotation result and exposes action methods
    that submit a decision back to the Avala platform.

    Example::

        @agent.on("result.submitted")
        def review(context: ResultContext) -> None:
            if not context.result_data:
                context.reject("No annotations provided")
            else:
                context.approve()
    """

    execution_uid: str
    event_type: str
    task_uid: str
    result_uid: str
    result_data: list[dict[str, Any]]
    result_metadata: dict[str, Any]
    task_name: str | None
    task_type: str | None
    project_uid: str | None

    # Internal reference — not part of the public API.
    _agent: TaskAgent = field(repr=False)

    def approve(self, reason: str = "") -> None:
        """Approve this result and advance it through the workflow."""
        self._agent._submit_action(self.execution_uid, "approve", reason)

    def reject(self, reason: str = "") -> None:
        """Reject this result, returning it to the annotator for correction.

        Args:
            reason: Human-readable explanation shown to the annotator.
        """
        self._agent._submit_action(self.execution_uid, "reject", reason)

    def flag(self, reason: str = "") -> None:
        """Flag this result for manual human review.

        Args:
            reason: Human-readable explanation for the reviewer.
        """
        self._agent._submit_action(self.execution_uid, "flag", reason)

    def skip(self) -> None:
        """Acknowledge the execution without taking any workflow action."""
        self._agent._submit_action(self.execution_uid, "skip", "")


@dataclass
class TaskContext:
    """
    Context passed to handlers registered for task events.

    Provides access to the task state and exposes action methods
    that submit a decision back to the Avala platform.

    Example::

        @agent.on("task.completed")
        def on_complete(context: TaskContext) -> None:
            context.approve()
    """

    execution_uid: str
    event_type: str
    task_uid: str
    task_name: str | None
    task_type: str | None
    task_status: str | None
    project_uid: str | None

    # Internal reference — not part of the public API.
    _agent: TaskAgent = field(repr=False)

    def approve(self, reason: str = "") -> None:
        """Approve this task execution."""
        self._agent._submit_action(self.execution_uid, "approve", reason)

    def reject(self, reason: str = "") -> None:
        """Reject this task execution.

        Args:
            reason: Human-readable explanation.
        """
        self._agent._submit_action(self.execution_uid, "reject", reason)

    def flag(self, reason: str = "") -> None:
        """Flag this task execution for manual review.

        Args:
            reason: Human-readable explanation for the reviewer.
        """
        self._agent._submit_action(self.execution_uid, "flag", reason)

    def skip(self) -> None:
        """Acknowledge the execution without taking any workflow action."""
        self._agent._submit_action(self.execution_uid, "skip", "")


@dataclass
class EventContext:
    """
    Context passed to handlers for dataset and export events.

    These events carry resource-level metadata (not task/result data).
    Use :meth:`skip` to acknowledge without action, or any action
    method to submit a decision.

    Example::

        @agent.on("dataset.created")
        def on_dataset(context: EventContext) -> None:
            print(f"Dataset {context.resource_uid} created")
            context.skip()
    """

    execution_uid: str
    event_type: str
    resource_uid: str | None
    resource_type: str | None
    project_uid: str | None
    payload: dict[str, Any]

    # Internal reference — not part of the public API.
    _agent: TaskAgent = field(repr=False)

    def approve(self, reason: str = "") -> None:
        """Approve this event execution."""
        self._agent._submit_action(self.execution_uid, "approve", reason)

    def reject(self, reason: str = "") -> None:
        """Reject this event execution."""
        self._agent._submit_action(self.execution_uid, "reject", reason)

    def flag(self, reason: str = "") -> None:
        """Flag this event execution for manual review."""
        self._agent._submit_action(self.execution_uid, "flag", reason)

    def skip(self) -> None:
        """Acknowledge the execution without taking any workflow action."""
        self._agent._submit_action(self.execution_uid, "skip", "")
