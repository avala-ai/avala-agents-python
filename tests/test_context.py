"""Tests for ResultContext, TaskContext, and EventContext."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from avala_agents._context import EventContext, ResultContext, TaskContext


def _make_result_context(**kwargs: object) -> ResultContext:
    defaults = dict(
        execution_uid="exec-001",
        event_type="result.submitted",
        task_uid="task-001",
        result_uid="result-001",
        result_data=[{"label": "car"}],
        result_metadata={"confidence": 0.9},
        task_name="Test task",
        task_type="bounding_box",
        project_uid="proj-001",
        _agent=MagicMock(),
    )
    defaults.update(kwargs)
    return ResultContext(**defaults)  # type: ignore[arg-type]


def _make_task_context(**kwargs: object) -> TaskContext:
    defaults = dict(
        execution_uid="exec-002",
        event_type="task.completed",
        task_uid="task-002",
        task_name="Test task",
        task_type="bounding_box",
        task_status="completed",
        project_uid="proj-001",
        _agent=MagicMock(),
    )
    defaults.update(kwargs)
    return TaskContext(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ResultContext
# ---------------------------------------------------------------------------


class TestResultContext:
    def test_approve_calls_submit_action(self) -> None:
        ctx = _make_result_context()
        ctx.approve("LGTM")
        ctx._agent._submit_action.assert_called_once_with("exec-001", "approve", "LGTM")

    def test_approve_default_reason_is_empty(self) -> None:
        ctx = _make_result_context()
        ctx.approve()
        ctx._agent._submit_action.assert_called_once_with("exec-001", "approve", "")

    def test_reject_calls_submit_action(self) -> None:
        ctx = _make_result_context()
        ctx.reject("Too blurry")
        ctx._agent._submit_action.assert_called_once_with("exec-001", "reject", "Too blurry")

    def test_flag_calls_submit_action(self) -> None:
        ctx = _make_result_context()
        ctx.flag("Needs senior review")
        ctx._agent._submit_action.assert_called_once_with("exec-001", "flag", "Needs senior review")

    def test_skip_calls_submit_action_with_empty_reason(self) -> None:
        ctx = _make_result_context()
        ctx.skip()
        ctx._agent._submit_action.assert_called_once_with("exec-001", "skip", "")

    def test_result_data_accessible(self) -> None:
        ctx = _make_result_context(result_data=[{"label": "pedestrian"}])
        assert ctx.result_data == [{"label": "pedestrian"}]

    def test_metadata_accessible(self) -> None:
        ctx = _make_result_context(result_metadata={"confidence": 0.42})
        assert ctx.result_metadata["confidence"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# TaskContext
# ---------------------------------------------------------------------------


class TestTaskContext:
    def test_approve_calls_submit_action(self) -> None:
        ctx = _make_task_context()
        ctx.approve()
        ctx._agent._submit_action.assert_called_once_with("exec-002", "approve", "")

    def test_reject_calls_submit_action(self) -> None:
        ctx = _make_task_context()
        ctx.reject("Incomplete")
        ctx._agent._submit_action.assert_called_once_with("exec-002", "reject", "Incomplete")

    def test_flag_calls_submit_action(self) -> None:
        ctx = _make_task_context()
        ctx.flag("Unusual")
        ctx._agent._submit_action.assert_called_once_with("exec-002", "flag", "Unusual")

    def test_skip_calls_submit_action(self) -> None:
        ctx = _make_task_context()
        ctx.skip()
        ctx._agent._submit_action.assert_called_once_with("exec-002", "skip", "")

    def test_task_status_accessible(self) -> None:
        ctx = _make_task_context(task_status="completed")
        assert ctx.task_status == "completed"


# ---------------------------------------------------------------------------
# EventContext
# ---------------------------------------------------------------------------


def _make_event_context(**kwargs: object) -> EventContext:
    defaults = dict(
        execution_uid="exec-003",
        event_type="dataset.created",
        resource_uid="ds-001",
        resource_type="dataset",
        project_uid="proj-001",
        payload={"dataset_uid": "ds-001", "project_uid": "proj-001"},
        _agent=MagicMock(),
    )
    defaults.update(kwargs)
    return EventContext(**defaults)  # type: ignore[arg-type]


class TestEventContext:
    def test_approve_calls_submit_action(self) -> None:
        ctx = _make_event_context()
        ctx.approve("OK")
        ctx._agent._submit_action.assert_called_once_with("exec-003", "approve", "OK")

    def test_reject_calls_submit_action(self) -> None:
        ctx = _make_event_context()
        ctx.reject("Bad dataset")
        ctx._agent._submit_action.assert_called_once_with("exec-003", "reject", "Bad dataset")

    def test_flag_calls_submit_action(self) -> None:
        ctx = _make_event_context()
        ctx.flag("Review")
        ctx._agent._submit_action.assert_called_once_with("exec-003", "flag", "Review")

    def test_skip_calls_submit_action(self) -> None:
        ctx = _make_event_context()
        ctx.skip()
        ctx._agent._submit_action.assert_called_once_with("exec-003", "skip", "")

    def test_resource_uid_accessible(self) -> None:
        ctx = _make_event_context(resource_uid="ds-999")
        assert ctx.resource_uid == "ds-999"

    def test_resource_type_accessible(self) -> None:
        ctx = _make_event_context(resource_type="export")
        assert ctx.resource_type == "export"

    def test_payload_accessible(self) -> None:
        ctx = _make_event_context(payload={"key": "val"})
        assert ctx.payload == {"key": "val"}

    def test_resource_uid_none_for_unknown_events(self) -> None:
        ctx = _make_event_context(resource_uid=None, resource_type=None)
        assert ctx.resource_uid is None
        assert ctx.resource_type is None
