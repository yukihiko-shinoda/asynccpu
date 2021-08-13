"""Model module of process task."""
# Reason: To support Python 3.8 or less pylint: disable=unused-import
from asyncio.futures import Future
from logging import getLogger

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from typing import Any

import psutil

from asynccpu.subprocess import ProcessForWeakSet


class ProcessTask:
    """Model class of process task."""

    def __init__(self, process_for_week_set: ProcessForWeakSet, task: "Future[Any]") -> None:
        self.process_for_week_set = process_for_week_set
        self.task = task
        self.logger = getLogger(__name__)

    def cancel_if_not_cancelled(self) -> None:
        """Cancels task like future if its not cancelled."""
        self.logger.debug(self.task)
        cancelled = self.task.cancelled()
        self.logger.debug("Cancelled?: %s", cancelled)
        # This conditional return is just in case.
        # Cancelled task doesn't seems to come this line,
        # maybe they are removed from WeakSet by garbage collect.
        if cancelled:
            return
        cancel = self.task.cancel()
        self.logger.debug("Cancel succeed?: %s", cancel)
        if cancel:
            return
        try:
            psutil.Process(self.process_for_week_set.id).terminate()
        # Reason: Can't crate code to reach following line.
        except psutil.NoSuchProcess as error:  # pragma: no cover
            self.logger.debug("%s", error)
