"""Tests for the AgentError exception hierarchy."""

from __future__ import annotations

from avala_agents._exceptions import (
    AgentActionError,
    AgentError,
    AgentRegistrationError,
    AgentTimeoutError,
)


def test_agent_error_is_exception() -> None:
    assert issubclass(AgentError, Exception)


def test_agent_timeout_error_inherits_agent_error() -> None:
    assert issubclass(AgentTimeoutError, AgentError)


def test_agent_action_error_inherits_agent_error() -> None:
    assert issubclass(AgentActionError, AgentError)


def test_agent_registration_error_inherits_agent_error() -> None:
    assert issubclass(AgentRegistrationError, AgentError)


def test_agent_action_error_stores_status_code() -> None:
    err = AgentActionError("Failed", status_code=400)
    assert err.status_code == 400
    assert str(err) == "Failed"


def test_agent_registration_error_stores_status_code() -> None:
    err = AgentRegistrationError("Cannot register", status_code=503)
    assert err.status_code == 503


def test_agent_action_error_status_code_optional() -> None:
    err = AgentActionError("Network error")
    assert err.status_code is None
