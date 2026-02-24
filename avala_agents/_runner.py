"""Polling runner for the TaskAgent."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from avala_agents._agent import TaskAgent

logger = logging.getLogger(__name__)


class PollingRunner:
    """
    Polls the Avala agent executions API for pending work and dispatches
    events to the registered handlers on the parent :class:`TaskAgent`.

    Args:
        agent: The :class:`TaskAgent` that owns this runner.
        poll_interval: Seconds to wait between polls when no work is found.
    """

    def __init__(self, agent: TaskAgent, poll_interval: float = 5.0) -> None:
        self._agent = agent
        self._poll_interval = poll_interval
        self._running = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the blocking polling loop.

        This method blocks indefinitely.  Interrupt it with a
        :exc:`KeyboardInterrupt` (Ctrl-C) or call :meth:`stop` from a
        separate thread.
        """
        self._running = True
        logger.info(
            "Agent '%s' started polling (interval=%.1fs).",
            self._agent.name,
            self._poll_interval,
        )
        try:
            while self._running:
                processed = self.run_once()
                if processed == 0:
                    # Nothing to do — wait before the next poll.
                    time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            logger.info("Agent '%s' interrupted — shutting down.", self._agent.name)
        finally:
            self._running = False

    def run_once(self) -> int:
        """Execute a single poll iteration.

        Fetches pending executions and dispatches each one to the
        appropriate handler.

        Returns:
            The number of executions that were processed.
        """
        executions = self._agent._fetch_pending_executions()
        count = 0
        for execution in executions:
            try:
                self._agent._dispatch(execution)
                count += 1
            except Exception:
                execution_uid = execution.get("uid", "")
                logger.exception(
                    "Unhandled error while processing execution '%s'.",
                    execution_uid,
                )
                # Submit a skip action so the execution does not stay
                # stuck in RUNNING until the server-side timeout fires.
                try:
                    self._agent._submit_action(
                        execution_uid, "skip", "handler raised an unhandled exception"
                    )
                except Exception:
                    logger.warning(
                        "Failed to submit skip action for execution '%s'.",
                        execution_uid,
                        exc_info=True,
                    )
        return count

    def stop(self) -> None:
        """Signal the polling loop to stop after the current iteration."""
        self._running = False
