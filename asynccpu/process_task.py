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

    def send_signal(self, signal_number: int) -> None:
        """Cancels task like future if its not cancelled."""
        try:
            psutil.Process(self.process_for_week_set.id).send_signal(signal_number)
        # Reason: Can't crate code to reach following line.
        except psutil.NoSuchProcess as error:  # pragma: no cover
            self.logger.debug("%s", error)
