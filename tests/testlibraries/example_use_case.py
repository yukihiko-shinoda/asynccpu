"""The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
import asyncio
import os

# Reason: To support Python 3.8 or less pylint: disable=unused-import
import queue
import time
from asyncio.futures import Future

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from logging import DEBUG, LogRecord, getLogger
from logging.handlers import QueueHandler
from typing import Any, Callable, Generator, List, Optional

import pytest

# Reason: Following export method in __init__.py from Effective Python 2nd Edition item 85
from asynccpu import ProcessTaskPoolExecutor  # type: ignore
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.cpu_bound import process_cpu_bound
from tests.testlibraries.future_waiter import FutureWaiter
from tests.testlibraries.local_socket import LocalSocket


async def create_example_process_tasks(executor: ProcessTaskPoolExecutor) -> List["Future[str]"]:
    """Creates example process tasks."""
    futures = []
    for task_id in range(10):
        futures.append(executor.create_process_task(process_cpu_bound, task_id))
        # In case of new window in Windows, this method seems to occupy CPU resource in case when without sleep.
        # Otherwise, this method never releases CPU resource until all of CPU bound process finish.
        print("Sleep")
        await asyncio.sleep(0.001)
    return futures


async def example_use_case(
    queue_logger: Optional["queue.Queue[LogRecord]"] = None, configurer: Optional[Callable[[], Any]] = None
) -> List[str]:
    """The example use case of ProcessTaskPoolExecutor for E2E testing."""
    with ProcessTaskPoolExecutor(
        max_workers=3, cancel_tasks_when_shutdown=True, queue=queue_logger, configurer=configurer
    ) as executor:
        futures = await create_example_process_tasks(executor)
        return await asyncio.gather(*futures)


def example_use_case_method(queue_logger: Optional["queue.Queue[LogRecord]"] = None) -> Generator[str, None, None]:
    with ProcessTaskPoolExecutor(max_workers=3, cancel_tasks_when_shutdown=True, queue=queue_logger) as executor:
        futures = (executor.create_process_task(process_cpu_bound, x) for x in range(10))
        FutureWaiter.wait(futures)
        return (future.result() for future in futures)


def example_use_case_cancel_repost_process_id(
    queue_sub: Optional["queue.Queue[LogRecord]"] = None, queue_main: Optional["queue.Queue[LogRecord]"] = None
) -> None:
    """The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
    time.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
    LocalSocket.send(str(os.getpid()))
    if queue_main:
        logger = getLogger()
        logger.addHandler(QueueHandler(queue_main))
        logger.setLevel(DEBUG)
    results = example_use_case_method(queue_sub)
    results_string = repr(results)
    LocalSocket.send(results_string)
    pytest.fail(results_string)
