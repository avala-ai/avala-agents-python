"""Tests for PollingRunner."""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_runner(executions: list[dict], *, poll_interval: float = 5.0):  # type: ignore[return]
    """Return a PollingRunner wired to a mock agent."""
    from avala_agents._runner import PollingRunner

    agent = MagicMock()
    agent.name = "test-agent"
    agent._fetch_pending_executions.return_value = executions
    runner = PollingRunner(agent, poll_interval=poll_interval)
    return runner, agent


def test_run_once_returns_zero_when_no_executions() -> None:
    runner, _ = _make_runner([])
    assert runner.run_once() == 0


def test_run_once_returns_count_of_processed_executions() -> None:
    executions = [{"uid": "e1"}, {"uid": "e2"}]
    runner, agent = _make_runner(executions)
    count = runner.run_once()
    assert count == 2


def test_run_once_calls_dispatch_for_each_execution() -> None:
    executions = [{"uid": "e1"}, {"uid": "e2"}]
    runner, agent = _make_runner(executions)
    runner.run_once()
    assert agent._dispatch.call_count == 2
    agent._dispatch.assert_any_call({"uid": "e1"})
    agent._dispatch.assert_any_call({"uid": "e2"})


def test_run_once_continues_after_dispatch_exception() -> None:
    """A handler exception for one execution should not abort the rest."""
    executions = [{"uid": "e1"}, {"uid": "e2"}]
    runner, agent = _make_runner(executions)
    agent._dispatch.side_effect = [RuntimeError("oops"), None]

    # Should not raise; e2 must still be dispatched.
    count = runner.run_once()
    # Only e2 counted (e1 raised an exception).
    assert count == 1
    assert agent._dispatch.call_count == 2


def test_stop_sets_running_false() -> None:
    runner, _ = _make_runner([])
    runner._running = True
    runner.stop()
    assert runner._running is False


def test_run_stops_on_keyboard_interrupt() -> None:
    """run() should exit cleanly on KeyboardInterrupt."""
    from avala_agents._runner import PollingRunner

    agent = MagicMock()
    agent.name = "test-agent"
    call_count = 0

    def fake_run_once() -> int:
        nonlocal call_count
        call_count += 1
        raise KeyboardInterrupt

    runner = PollingRunner(agent, poll_interval=0.0)
    runner.run_once = fake_run_once  # type: ignore[method-assign]

    # Should not propagate KeyboardInterrupt.
    runner.run()
    assert call_count == 1
    assert runner._running is False
