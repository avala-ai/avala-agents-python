"""Event types and constants for avala-agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# All event identifiers the agent framework can handle.
# Must stay in sync with server/apps/agent/constants.py ALL_AGENT_EVENTS.
AGENT_EVENTS = [
    "dataset.created",
    "dataset.updated",
    "dataset.deleted",
    "export.completed",
    "export.failed",
    "task.completed",
    "result.submitted",
    "result.accepted",
    "result.rejected",
]

# Events whose execution payload contains result-level data.
RESULT_EVENTS = {
    "result.submitted",
    "result.accepted",
    "result.rejected",
}

# Events whose execution payload contains task-level data.
TASK_EVENTS = {
    "task.completed",
}

# Events whose execution payload contains dataset-level data.
DATASET_EVENTS = {
    "dataset.created",
    "dataset.updated",
    "dataset.deleted",
}

# Events whose execution payload contains export-level data.
EXPORT_EVENTS = {
    "export.completed",
    "export.failed",
}

# Valid action values accepted by POST /api/v1/agent-actions/.
VALID_ACTIONS = {"approve", "reject", "flag", "skip"}


@dataclass
class AgentEvent:
    """Raw event received from the agent executions API."""

    execution_uid: str
    event_type: str
    payload: dict[str, Any]
