"""Tests for _types module."""

from __future__ import annotations

from avala_agents._types import (
    AGENT_EVENTS,
    DATASET_EVENTS,
    EXPORT_EVENTS,
    RESULT_EVENTS,
    TASK_EVENTS,
    AgentEvent,
)


def test_agent_events_contains_expected_events() -> None:
    expected = {
        "dataset.created",
        "dataset.updated",
        "dataset.deleted",
        "export.completed",
        "export.failed",
        "task.completed",
        "result.submitted",
        "result.accepted",
        "result.rejected",
    }
    assert set(AGENT_EVENTS) == expected


def test_result_events_are_subset_of_agent_events() -> None:
    assert RESULT_EVENTS.issubset(set(AGENT_EVENTS))


def test_task_events_are_subset_of_agent_events() -> None:
    assert TASK_EVENTS.issubset(set(AGENT_EVENTS))


def test_dataset_events_are_subset_of_agent_events() -> None:
    assert DATASET_EVENTS.issubset(set(AGENT_EVENTS))


def test_export_events_are_subset_of_agent_events() -> None:
    assert EXPORT_EVENTS.issubset(set(AGENT_EVENTS))


def test_result_and_task_events_are_disjoint() -> None:
    assert RESULT_EVENTS.isdisjoint(TASK_EVENTS)


def test_agent_event_dataclass() -> None:
    event = AgentEvent(
        execution_uid="exec-001",
        event_type="result.submitted",
        payload={"key": "value"},
    )
    assert event.execution_uid == "exec-001"
    assert event.event_type == "result.submitted"
    assert event.payload == {"key": "value"}
