"""
Cpu bound.
see: https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools
"""

import os
import time
from logging import getLogger
from multiprocessing.connection import Connection
from signal import SIGTERM, signal
from typing import Any, NoReturn, Optional

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_MIDDLE
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket


async def process_cpu_bound(task_id: Optional[int] = None, send_process_id: bool = False) -> str:
    return cpu_bound(task_id, send_process_id)


def process_cpu_bound_method(
    task_id: Optional[int] = None, send_process_id: bool = False, connection: Optional[Connection] = None
) -> None:
    result = cpu_bound(task_id, send_process_id)
    if connection:
        connection.send(result)


def cpu_bound(task_id: Optional[int] = None, send_process_id: bool = False) -> str:
    """
    CPU-bound operations will block the event loop:
    in general it is preferable to run them in a process pool.
    """
    logger = getLogger(__name__)

    def hander(_signum: int, _frame: Optional[Any]) -> NoReturn:
        logger.info("CPU-bound: Terminate")
        raise Terminated()

    signal(SIGTERM, hander)
    process_id = os.getpid()
    print(process_id)
    logger.info("CPU-bound: process id = %d", process_id)
    if send_process_id:
        time.sleep(SECOND_SLEEP_FOR_TEST_MIDDLE)
        logger.info("CPU-bound: Send process id")
        LocalSocket.send(str(process_id))
    logger.info("CPU-bound: Start")
    result = sum(i * i for i in range(10 ** 7))
    logger.debug("CPU-bound: Finish")
    return ("" if task_id is None else f"task_id: {task_id}, ") + f"result: {result}"


def expect_process_cpu_bound(task_id: Optional[int] = None) -> str:
    return ("" if task_id is None else f"task_id: {task_id}, ") + "result: 333333283333335000000"
