"""Tests for TaskAgent."""

from __future__ import annotations

import httpx
import pytest
import respx

from avala_agents import TaskAgent
from avala_agents._exceptions import AgentActionError, AgentRegistrationError
from tests.conftest import (
    BASE_URL,
    PENDING_EXECUTION_RESULT,
    PENDING_EXECUTION_TASK,
    REGISTER_RESPONSE,
)

AGENT_UID = REGISTER_RESPONSE["uid"]


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


def test_agent_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """TaskAgent raises ValueError when no API key is available."""
    monkeypatch.delenv("AVALA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="No API key"):
        TaskAgent()


def test_agent_accepts_explicit_api_key() -> None:
    """TaskAgent can be created with an explicit API key."""
    agent = TaskAgent(api_key="avk_test")
    assert agent.name == "default-agent"
    agent.close()


def test_agent_accepts_env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """TaskAgent falls back to AVALA_API_KEY environment variable."""
    monkeypatch.setenv("AVALA_API_KEY", "avk_from_env")
    agent = TaskAgent()
    agent.close()


def test_agent_custom_name_and_project() -> None:
    """TaskAgent stores name and project attributes."""
    agent = TaskAgent(api_key="avk_test", name="my-agent", project="proj-x")
    assert agent.name == "my-agent"
    assert agent._project == "proj-x"
    agent.close()


def test_agent_context_manager() -> None:
    """TaskAgent works as a context manager."""
    with TaskAgent(api_key="avk_test") as agent:
        assert agent is not None


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def test_on_decorator_registers_handler() -> None:
    """@agent.on registers the handler under the correct event key."""
    agent = TaskAgent(api_key="avk_test")

    @agent.on("result.submitted")
    def handler(ctx):  # type: ignore[no-untyped-def]
        pass

    assert "result.submitted" in agent._handlers
    assert agent._handlers["result.submitted"] is handler
    agent.close()


def test_on_decorator_returns_original_function() -> None:
    """@agent.on returns the unmodified handler function."""
    agent = TaskAgent(api_key="avk_test")

    @agent.on("task.completed")
    def my_handler(ctx):  # type: ignore[no-untyped-def]
        return "result"

    assert my_handler(None) == "result"
    agent.close()


def test_on_decorator_raises_for_unknown_event() -> None:
    """@agent.on raises ValueError for an unrecognised event name."""
    agent = TaskAgent(api_key="avk_test")
    with pytest.raises(ValueError, match="Unknown event"):
        agent.on("bogus.event")
    agent.close()


def test_multiple_handlers_can_be_registered() -> None:
    """Multiple distinct event handlers can be registered."""
    agent = TaskAgent(api_key="avk_test")

    @agent.on("result.submitted")
    def h1(ctx):  # type: ignore[no-untyped-def]
        pass

    @agent.on("task.completed")
    def h2(ctx):  # type: ignore[no-untyped-def]
        pass

    assert len(agent._handlers) == 2
    agent.close()


# ---------------------------------------------------------------------------
# Registration with server
# ---------------------------------------------------------------------------


@respx.mock
def test_register_posts_to_agents_endpoint() -> None:
    """_register() POSTs to /agents/ and stores the returned uid."""
    route = respx.post(f"{BASE_URL}/agents/").mock(return_value=httpx.Response(201, json=REGISTER_RESPONSE))
    agent = TaskAgent(api_key="avk_test", name="test-agent")
    agent._register()

    assert route.called
    assert agent._agent_uid == AGENT_UID
    agent.close()


@respx.mock
def test_register_is_idempotent() -> None:
    """_register() does not POST again if already registered."""
    route = respx.post(f"{BASE_URL}/agents/").mock(return_value=httpx.Response(201, json=REGISTER_RESPONSE))
    agent = TaskAgent(api_key="avk_test", name="test-agent")
    agent._register()
    agent._register()

    assert route.call_count == 1
    agent.close()


@respx.mock
def test_register_raises_on_server_error() -> None:
    """_register() raises AgentRegistrationError on non-2xx response."""
    respx.post(f"{BASE_URL}/agents/").mock(return_value=httpx.Response(500, json={"detail": "Internal Server Error"}))
    agent = TaskAgent(api_key="avk_test")
    with pytest.raises(AgentRegistrationError, match="HTTP 500"):
        agent._register()
    agent.close()


@respx.mock
def test_register_includes_project_when_set() -> None:
    """_register() includes project in the POST body when configured."""
    route = respx.post(f"{BASE_URL}/agents/").mock(return_value=httpx.Response(201, json=REGISTER_RESPONSE))
    agent = TaskAgent(api_key="avk_test", project="proj-001")
    agent._register()

    sent = route.calls.last.request
    import json

    body = json.loads(sent.content)
    assert body["project"] == "proj-001"
    agent.close()


@respx.mock
def test_register_includes_subscribed_events() -> None:
    """_register() includes the registered event names in the payload."""
    route = respx.post(f"{BASE_URL}/agents/").mock(return_value=httpx.Response(201, json=REGISTER_RESPONSE))
    agent = TaskAgent(api_key="avk_test")

    @agent.on("result.submitted")
    def h(ctx):  # type: ignore[no-untyped-def]
        pass

    agent._register()

    import json

    body = json.loads(route.calls.last.request.content)
    assert "result.submitted" in body["events"]
    agent.close()


# ---------------------------------------------------------------------------
# Fetching executions
# ---------------------------------------------------------------------------


@respx.mock
def test_fetch_pending_executions_returns_list() -> None:
    """_fetch_pending_executions() returns a list of execution dicts."""
    agent = TaskAgent(api_key="avk_test")
    agent._agent_uid = AGENT_UID

    respx.get(f"{BASE_URL}/agents/{AGENT_UID}/executions/").mock(
        return_value=httpx.Response(
            200,
            json={"results": [PENDING_EXECUTION_RESULT], "next": None},
        )
    )

    executions = agent._fetch_pending_executions()
    assert len(executions) == 1
    assert executions[0]["uid"] == PENDING_EXECUTION_RESULT["uid"]
    agent.close()


@respx.mock
def test_fetch_pending_executions_returns_empty_on_error() -> None:
    """_fetch_pending_executions() returns [] on a server error (no exception)."""
    agent = TaskAgent(api_key="avk_test")
    agent._agent_uid = AGENT_UID

    respx.get(f"{BASE_URL}/agents/{AGENT_UID}/executions/").mock(return_value=httpx.Response(503, json={}))

    executions = agent._fetch_pending_executions()
    assert executions == []
    agent.close()


def test_fetch_pending_executions_returns_empty_when_not_registered() -> None:
    """_fetch_pending_executions() returns [] when agent_uid is not set."""
    agent = TaskAgent(api_key="avk_test")
    # _agent_uid is None by default
    assert agent._fetch_pending_executions() == []
    agent.close()


# ---------------------------------------------------------------------------
# Action submission
# ---------------------------------------------------------------------------


@respx.mock
def test_submit_action_posts_to_agent_actions() -> None:
    """_submit_action() POSTs to /agent-actions/ with correct body."""
    route = respx.post(f"{BASE_URL}/agent-actions/").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    exec_uid = PENDING_EXECUTION_RESULT["uid"]
    agent = TaskAgent(api_key="avk_test")
    agent._submit_action(exec_uid, "approve", "Looks good")

    import json

    body = json.loads(route.calls.last.request.content)
    assert body["execution"] == exec_uid
    assert body["action"] == "approve"
    assert body["reason"] == "Looks good"
    agent.close()


@respx.mock
def test_submit_action_omits_reason_when_empty() -> None:
    """_submit_action() omits 'reason' from the payload when empty."""
    route = respx.post(f"{BASE_URL}/agent-actions/").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    agent = TaskAgent(api_key="avk_test")
    agent._submit_action(PENDING_EXECUTION_RESULT["uid"], "approve", "")

    import json

    body = json.loads(route.calls.last.request.content)
    assert "reason" not in body
    agent.close()


@respx.mock
def test_submit_action_raises_on_server_error() -> None:
    """_submit_action() raises AgentActionError on non-2xx response."""
    respx.post(f"{BASE_URL}/agent-actions/").mock(return_value=httpx.Response(400, json={"detail": "Bad request"}))
    agent = TaskAgent(api_key="avk_test")
    with pytest.raises(AgentActionError, match="HTTP 400"):
        agent._submit_action(PENDING_EXECUTION_RESULT["uid"], "approve", "")
    agent.close()


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


def test_build_context_result_event() -> None:
    """_build_context() returns a ResultContext for result events."""
    from avala_agents._context import ResultContext
    from avala_agents._types import AgentEvent

    agent = TaskAgent(api_key="avk_test")
    payload = PENDING_EXECUTION_RESULT["event_payload"]
    event = AgentEvent(
        execution_uid=PENDING_EXECUTION_RESULT["uid"],
        event_type="result.submitted",
        payload=payload,
    )
    ctx = agent._build_context(event)
    assert isinstance(ctx, ResultContext)
    assert ctx.result_uid == payload["result_uid"]
    assert ctx.task_uid == payload["task_uid"]
    assert ctx.result_data == [{"label": "car", "bbox": [10, 20, 100, 200]}]
    assert ctx.result_metadata == {"confidence": 0.95}
    assert ctx.project_uid == payload["project_uid"]
    agent.close()


def test_build_context_task_event() -> None:
    """_build_context() returns a TaskContext for task events."""
    from avala_agents._context import TaskContext
    from avala_agents._types import AgentEvent

    agent = TaskAgent(api_key="avk_test")
    payload = PENDING_EXECUTION_TASK["event_payload"]
    event = AgentEvent(
        execution_uid=PENDING_EXECUTION_TASK["uid"],
        event_type="task.completed",
        payload=payload,
    )
    ctx = agent._build_context(event)
    assert isinstance(ctx, TaskContext)
    assert ctx.task_uid == payload["task_uid"]
    assert ctx.task_status == "completed"
    agent.close()


def test_build_context_dataset_event() -> None:
    """_build_context() returns an EventContext for dataset events."""
    from avala_agents._context import EventContext
    from avala_agents._types import AgentEvent

    agent = TaskAgent(api_key="avk_test")
    payload = {
        "dataset_uid": "00000000-0000-4000-8000-000000000050",
        "project_uid": "00000000-0000-4000-8000-000000000040",
    }
    event = AgentEvent(
        execution_uid="00000000-0000-4000-8000-000000000099",
        event_type="dataset.created",
        payload=payload,
    )
    ctx = agent._build_context(event)
    assert isinstance(ctx, EventContext)
    assert ctx.resource_uid == payload["dataset_uid"]
    assert ctx.resource_type == "dataset"
    assert ctx.project_uid == payload["project_uid"]
    assert ctx.payload is payload
    agent.close()


def test_build_context_export_event() -> None:
    """_build_context() returns an EventContext for export events."""
    from avala_agents._context import EventContext
    from avala_agents._types import AgentEvent

    agent = TaskAgent(api_key="avk_test")
    payload = {
        "export_uid": "00000000-0000-4000-8000-000000000060",
        "project_uid": "00000000-0000-4000-8000-000000000040",
    }
    event = AgentEvent(
        execution_uid="00000000-0000-4000-8000-000000000098",
        event_type="export.completed",
        payload=payload,
    )
    ctx = agent._build_context(event)
    assert isinstance(ctx, EventContext)
    assert ctx.resource_uid == payload["export_uid"]
    assert ctx.resource_type == "export"
    agent.close()


def test_build_context_unknown_event_uses_fallback() -> None:
    """_build_context() returns EventContext with resource_type=None for unknown events."""
    from avala_agents._context import EventContext
    from avala_agents._types import AgentEvent

    agent = TaskAgent(api_key="avk_test")
    event = AgentEvent(
        execution_uid="00000000-0000-4000-8000-000000000097",
        event_type="future.event",
        payload={"some_key": "value"},
    )
    ctx = agent._build_context(event)
    assert isinstance(ctx, EventContext)
    assert ctx.resource_uid is None
    assert ctx.resource_type is None
    agent.close()


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


@respx.mock
def test_dispatch_calls_handler_and_does_not_auto_skip() -> None:
    """_dispatch() calls the registered handler; handler controls the action."""
    action_route = respx.post(f"{BASE_URL}/agent-actions/").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    agent = TaskAgent(api_key="avk_test")

    calls: list[object] = []

    @agent.on("result.submitted")
    def handler(ctx):  # type: ignore[no-untyped-def]
        calls.append(ctx)
        ctx.approve()

    agent._dispatch(PENDING_EXECUTION_RESULT)

    assert len(calls) == 1
    assert action_route.call_count == 1

    import json

    body = json.loads(action_route.calls.last.request.content)
    assert body["action"] == "approve"
    agent.close()


@respx.mock
def test_dispatch_auto_skips_when_no_handler() -> None:
    """_dispatch() submits 'skip' automatically for unhandled event types."""
    route = respx.post(f"{BASE_URL}/agent-actions/").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    agent = TaskAgent(api_key="avk_test")
    # No handlers registered.
    agent._dispatch(PENDING_EXECUTION_RESULT)

    import json

    body = json.loads(route.calls.last.request.content)
    assert body["action"] == "skip"
    agent.close()


# ---------------------------------------------------------------------------
# run_once integration
# ---------------------------------------------------------------------------


@respx.mock
def test_run_once_returns_count() -> None:
    """run_once() processes pending executions and returns the count."""
    respx.post(f"{BASE_URL}/agents/").mock(return_value=httpx.Response(201, json=REGISTER_RESPONSE))
    respx.get(f"{BASE_URL}/agents/{AGENT_UID}/executions/").mock(
        return_value=httpx.Response(
            200,
            json={"results": [PENDING_EXECUTION_RESULT, PENDING_EXECUTION_TASK]},
        )
    )
    respx.post(f"{BASE_URL}/agent-actions/").mock(return_value=httpx.Response(200, json={"status": "ok"}))

    agent = TaskAgent(api_key="avk_test", name="test-agent")

    @agent.on("result.submitted")
    def h1(ctx):  # type: ignore[no-untyped-def]
        ctx.approve()

    @agent.on("task.completed")
    def h2(ctx):  # type: ignore[no-untyped-def]
        ctx.approve()

    count = agent.run_once()
    assert count == 2
    agent.close()
