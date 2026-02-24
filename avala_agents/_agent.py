"""TaskAgent — main entry point for the avala-agents SDK."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

import httpx

from avala_agents._context import EventContext, ResultContext, TaskContext
from avala_agents._exceptions import AgentActionError, AgentRegistrationError, AgentTimeoutError
from avala_agents._runner import PollingRunner
from avala_agents._types import (
    AGENT_EVENTS,
    DATASET_EVENTS,
    EXPORT_EVENTS,
    RESULT_EVENTS,
    TASK_EVENTS,
    AgentEvent,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.avala.ai/api/v1"


class TaskAgent:
    """
    An agent that processes annotation workflow events.

    The agent polls the Avala API for pending executions, calls the
    matching handler, and submits the resulting action back to the
    platform.

    Args:
        api_key: Avala API key (``avk_...``).  Falls back to the
            ``AVALA_API_KEY`` environment variable.
        base_url: Override the API base URL.  Falls back to the
            ``AVALA_BASE_URL`` environment variable, then the production
            default.
        name: Logical name for this agent instance.  Used to identify
            the agent in the Avala dashboard.
        project: Optional project UID.  When set, only executions
            belonging to that project are returned.
        task_types: Optional list of task type identifiers to filter on.
        poll_interval: Seconds between polling requests when the queue
            is empty.

    Usage::

        from avala_agents import TaskAgent

        agent = TaskAgent(api_key="avk_...", name="quality-checker")

        @agent.on("result.submitted")
        def check(context):
            if not context.result_data:
                context.reject("No annotations found")
            else:
                context.approve()

        agent.run()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        name: str = "default-agent",
        project: str | None = None,
        task_types: list[str] | None = None,
        poll_interval: float = 5.0,
    ) -> None:
        resolved_key = api_key or os.environ.get("AVALA_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "No API key provided. "
                "Pass api_key= or set the AVALA_API_KEY environment variable."
            )
        resolved_url = (
            base_url
            or os.environ.get("AVALA_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/") + "/"

        self.name = name
        self._project = project
        self._task_types = task_types or []
        self._poll_interval = poll_interval
        self._base_url = resolved_url
        self._handlers: dict[str, Callable[..., None]] = {}
        self._agent_uid: str | None = None

        self._http = httpx.Client(
            base_url=resolved_url,
            headers={
                "X-Avala-Api-Key": resolved_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on(self, event: str) -> Callable[[Callable[..., None]], Callable[..., None]]:
        """Decorator — register a handler for an agent event.

        Args:
            event: One of the supported event identifiers
                (``"result.submitted"``, ``"result.accepted"``,
                ``"result.rejected"``, ``"task.completed"``).

        Returns:
            The original handler function, unchanged.

        Raises:
            ValueError: If ``event`` is not a recognised event identifier.

        Example::

            @agent.on("result.submitted")
            def handle(context):
                context.approve()
        """
        if event not in AGENT_EVENTS:
            raise ValueError(
                f"Unknown event '{event}'. "
                f"Supported events: {', '.join(AGENT_EVENTS)}"
            )

        def decorator(func: Callable[..., None]) -> Callable[..., None]:
            self._handlers[event] = func
            logger.debug("Registered handler for '%s'.", event)
            return func

        return decorator

    def run(self) -> None:
        """Start the blocking polling loop.

        Registers the agent with the server on first call, then polls
        indefinitely for pending executions.  Interrupt with
        ``Ctrl-C``.
        """
        self._register()
        runner = PollingRunner(self, poll_interval=self._poll_interval)
        runner.run()

    def run_once(self) -> int:
        """Process all currently pending executions once (non-blocking).

        Registers the agent with the server if not already registered,
        processes pending executions, and returns.

        Returns:
            Number of executions processed.
        """
        self._register()
        runner = PollingRunner(self, poll_interval=self._poll_interval)
        return runner.run_once()

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> TaskAgent:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers called by PollingRunner and context objects
    # ------------------------------------------------------------------

    def _register(self) -> None:
        """Register (or update) this agent on the server.

        Idempotent — safe to call multiple times.  Sets
        ``self._agent_uid`` on success.

        Raises:
            AgentRegistrationError: If the server returns a non-2xx
                response.
        """
        if self._agent_uid is not None:
            return  # Already registered in this session.

        payload: dict[str, Any] = {
            "name": self.name,
            "events": list(self._handlers.keys()),
        }
        if self._project:
            payload["project"] = self._project
        if self._task_types:
            payload["task_types"] = self._task_types

        try:
            response = self._http.post("agents/", json=payload)
        except httpx.TimeoutException as exc:
            raise AgentTimeoutError(f"Timed out during registration: {exc}") from exc
        except httpx.HTTPError as exc:
            raise AgentRegistrationError(f"Network error during registration: {exc}") from exc

        if not response.is_success:
            raise AgentRegistrationError(
                f"Failed to register agent '{self.name}': "
                f"HTTP {response.status_code}",
                status_code=response.status_code,
            )

        data = response.json()
        self._agent_uid = data.get("uid")
        if not self._agent_uid:
            raise AgentRegistrationError(
                f"Server returned success but no agent UID for '{self.name}'. "
                f"Response: {data}",
            )
        logger.info(
            "Agent '%s' registered (uid=%s).",
            self.name,
            self._agent_uid,
        )

    def _fetch_pending_executions(self) -> list[dict[str, Any]]:
        """Poll the server for pending executions assigned to this agent.

        Returns:
            A list of raw execution dicts from the API.  Empty when
            there is nothing to process.
        """
        if not self._agent_uid:
            logger.warning("Cannot fetch executions — agent not registered.")
            return []

        params: dict[str, Any] = {"status": "pending"}
        if self._project:
            params["project"] = self._project
        if self._task_types:
            params["task_types"] = ",".join(self._task_types)

        try:
            response = self._http.get(
                f"agents/{self._agent_uid}/executions/",
                params=params,
            )
        except httpx.HTTPError as exc:
            logger.error("Network error while fetching executions: %s", exc)
            return []

        if not response.is_success:
            logger.error(
                "Failed to fetch executions: HTTP %s",
                response.status_code,
            )
            return []

        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("results", [])
        return []

    def _dispatch(self, execution: dict[str, Any]) -> None:
        """Dispatch a single execution dict to its registered handler.

        If no handler is registered for the execution's event type,
        the execution is skipped automatically.

        Args:
            execution: Raw execution payload from the API.
        """
        execution_uid: str = execution.get("uid", "")
        event_type: str = execution.get("event_type", "")
        payload: dict[str, Any] = execution.get("event_payload", {})

        event = AgentEvent(
            execution_uid=execution_uid,
            event_type=event_type,
            payload=payload,
        )

        handler = self._handlers.get(event_type)
        if handler is None:
            reason = f"No handler registered for event type '{event_type}'"
            logger.warning(
                "No handler for event '%s' (execution %s) — skipping. "
                "Register a handler with @agent.on('%s') to process these events.",
                event_type,
                execution_uid,
                event_type,
            )
            self._submit_action(execution_uid, "skip", reason)
            return

        context = self._build_context(event)
        logger.debug(
            "Dispatching execution '%s' (event=%s) to handler '%s'.",
            execution_uid,
            event_type,
            handler.__name__,
        )
        handler(context)

    def _build_context(
        self, event: AgentEvent
    ) -> ResultContext | TaskContext | EventContext:
        """Build the appropriate context object for *event*.

        Args:
            event: The raw :class:`AgentEvent` to wrap.

        Returns:
            A :class:`ResultContext` for result events, a
            :class:`TaskContext` for task events, or an
            :class:`EventContext` for dataset/export events.
        """
        p = event.payload

        if event.event_type in RESULT_EVENTS:
            return ResultContext(
                execution_uid=event.execution_uid,
                event_type=event.event_type,
                task_uid=p.get("task_uid", ""),
                result_uid=p.get("result_uid", ""),
                result_data=p.get("result_data", []),
                result_metadata=p.get("result_metadata", {}),
                task_name=p.get("task_name"),
                task_type=p.get("task_type"),
                project_uid=p.get("project_uid"),
                _agent=self,
            )

        if event.event_type in TASK_EVENTS:
            return TaskContext(
                execution_uid=event.execution_uid,
                event_type=event.event_type,
                task_uid=p.get("task_uid", ""),
                task_name=p.get("task_name"),
                task_type=p.get("task_type"),
                task_status=p.get("task_status"),
                project_uid=p.get("project_uid"),
                _agent=self,
            )

        if event.event_type in DATASET_EVENTS or event.event_type in EXPORT_EVENTS:
            return EventContext(
                execution_uid=event.execution_uid,
                event_type=event.event_type,
                resource_uid=p.get("dataset_uid") or p.get("export_uid"),
                resource_type=event.event_type.split(".")[0],
                project_uid=p.get("project_uid"),
                payload=p,
                _agent=self,
            )

        # Fallback: generic EventContext for forward-compatibility.
        logger.warning(
            "Unrecognised event type '%s' — using generic EventContext. "
            "Consider upgrading avala-agents to handle this event natively.",
            event.event_type,
        )
        return EventContext(
            execution_uid=event.execution_uid,
            event_type=event.event_type,
            resource_uid=None,
            resource_type=None,
            project_uid=p.get("project_uid"),
            payload=p,
            _agent=self,
        )

    def _submit_action(
        self, execution_uid: str, action: str, reason: str
    ) -> None:
        """POST an action decision to the server.

        Args:
            execution_uid: UID of the execution being resolved.
            action: One of ``approve``, ``reject``, ``flag``, ``skip``.
            reason: Human-readable explanation (may be empty).

        Raises:
            AgentActionError: If the server returns a non-2xx response.
        """
        payload: dict[str, Any] = {
            "execution": execution_uid,
            "action": action,
        }
        if reason:
            payload["reason"] = reason

        try:
            response = self._http.post("agent-actions/", json=payload)
        except httpx.TimeoutException as exc:
            raise AgentTimeoutError(
                f"Timed out while submitting action '{action}' "
                f"for execution '{execution_uid}': {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AgentActionError(
                f"Network error while submitting action '{action}' "
                f"for execution '{execution_uid}': {exc}"
            ) from exc

        if not response.is_success:
            raise AgentActionError(
                f"Failed to submit action '{action}' for execution "
                f"'{execution_uid}': HTTP {response.status_code}",
                status_code=response.status_code,
            )

        logger.debug(
            "Action '%s' submitted for execution '%s'.",
            action,
            execution_uid,
        )
