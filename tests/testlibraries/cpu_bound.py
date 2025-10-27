"""Cpu bound.

see: https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from datetime import timezone
from logging import getLogger
from signal import SIGTERM
from signal import signal
from typing import TYPE_CHECKING
from typing import NoReturn

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_MIDDLE
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket

if TYPE_CHECKING:
    from multiprocessing.connection import Connection
    from types import FrameType


# Reason: Executor function: create_process_task() doesn't support kwargs.
async def process_cpu_bound(task_id: int | None = None, send_process_id: bool = False) -> str:  # noqa: FBT001,FBT002
    return cpu_bound(task_id, send_process_id=send_process_id)


def process_cpu_bound_method(
    task_id: int | None = None,
    *,
    send_process_id: bool = False,
    connection: Connection | None = None,
) -> None:
    """The CPU-bound task for method."""
    result = cpu_bound(task_id, send_process_id=send_process_id)
    if connection:
        connection.send(result)


def log_info_keyboard_interrupt_for_windows(logger: logging.Logger) -> None:  # pragma: no cover
    """On Windows, directly create and emit a log record to ensure it reaches the queue.

    The standard logging might not work due to Windows/multiprocessing issues
    """
    root_logger = getLogger()

    # Try to manually put the log record on the queue if QueueHandler exists
    for log_handler in list(logger.handlers) + list(root_logger.handlers):
        if isinstance(log_handler, logging.handlers.QueueHandler):
            # Manually create a log record and emit it
            record = logger.makeRecord(
                logger.name,
                logging.INFO,
                __file__,
                73,
                "CPU-bound: KeyboardInterrupt",
                (),
                None,
            )
            log_handler.emit(record)
            # Try to flush/force delivery
            if hasattr(log_handler, "flush"):
                log_handler.flush()

    # Give time for the queue message to be delivered
    # On Windows this requires substantial time due to process boundaries and Manager overhead
    time.sleep(5.0)


def log_info_keyboard_interrupt(logger: logging.Logger) -> None:
    if sys.platform == "win32":  # pragma: no cover
        return log_info_keyboard_interrupt_for_windows(logger)
    return logger.info("CPU-bound: KeyboardInterrupt")


# Reason: Executor function: submit() doesn't support kwargs.
def cpu_bound(task_id: int | None = None, send_process_id: bool = False) -> str:  # noqa: FBT001,FBT002
    """Represents a CPU-bound task.

    CPU-bound operations will block the event loop:
    in general it is preferable to run them in a process pool.
    """
    try:
        logger = getLogger(__name__)

        def handler(_signum: int, _frame: FrameType | None) -> NoReturn:
            logger.info("CPU-bound: Terminate")
            raise Terminated

        signal(SIGTERM, handler)
        process_id = os.getpid()
        # Reason: This process may runs as asyncio task that cannot log by logger.
        print(process_id)  # noqa: T201
        logger.info("CPU-bound: process id = %d", process_id)
        if send_process_id:
            time.sleep(SECOND_SLEEP_FOR_TEST_MIDDLE)
            logger.info("CPU-bound: Send process id")
            LocalSocket.send(str(process_id))
        logger.info("CPU-bound: Start")
        result = sum(i * i for i in range(10**7))
        logger.debug("CPU-bound: Finish")
        logger.debug("%d %s", task_id, datetime.now(tz=timezone.utc))
        return ("" if task_id is None else f"task_id: {task_id}, ") + f"result: {result}"
    except KeyboardInterrupt:
        # Log the KeyboardInterrupt - this MUST reach the queue for the test to pass
        log_info_keyboard_interrupt(logger)
        raise


def expect_process_cpu_bound(task_id: int | None = None) -> str:
    return ("" if task_id is None else f"task_id: {task_id}, ") + "result: 333333283333335000000"
