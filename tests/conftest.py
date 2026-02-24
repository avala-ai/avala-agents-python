"""Shared pytest fixtures for avala-agents tests."""

from __future__ import annotations

BASE_URL = "https://api.avala.ai/api/v1"

REGISTER_RESPONSE = {"uid": "00000000-0000-4000-8000-000000000001", "name": "test-agent"}

PENDING_EXECUTION_RESULT = {
    "uid": "00000000-0000-4000-8000-000000000010",
    "event_type": "result.submitted",
    "event_payload": {
        "task_uid": "00000000-0000-4000-8000-000000000020",
        "result_uid": "00000000-0000-4000-8000-000000000030",
        "result_data": [{"label": "car", "bbox": [10, 20, 100, 200]}],
        "result_metadata": {"confidence": 0.95},
        "task_name": "Annotate vehicles",
        "task_type": "bounding_box",
        "project_uid": "00000000-0000-4000-8000-000000000040",
    },
}

PENDING_EXECUTION_TASK = {
    "uid": "00000000-0000-4000-8000-000000000011",
    "event_type": "task.completed",
    "event_payload": {
        "task_uid": "00000000-0000-4000-8000-000000000021",
        "task_name": "Annotate pedestrians",
        "task_type": "bounding_box",
        "task_status": "completed",
        "project_uid": "00000000-0000-4000-8000-000000000040",
    },
}
