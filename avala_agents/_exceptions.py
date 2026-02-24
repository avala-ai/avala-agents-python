"""Error hierarchy for avala-agents."""

from __future__ import annotations


class AgentError(Exception):
    """Base error for avala-agents."""


class AgentTimeoutError(AgentError):
    """Agent execution timed out."""


class AgentActionError(AgentError):
    """Failed to submit an agent action."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AgentRegistrationError(AgentError):
    """Failed to register or update the agent on the server."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
