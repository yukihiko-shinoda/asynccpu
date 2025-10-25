"""The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""

from __future__ import annotations

import asyncio
import os
import time
from logging import DEBUG
from logging import getLogger
from logging.handlers import QueueHandler
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Generator

import pytest

from asynccpu import ProcessTaskPoolExecutor
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.cpu_bound import process_cpu_bound
from tests.testlibraries.future_waiter import FutureWaiter
from tests.testlibraries.local_socket import LocalSocket

if TYPE_CHECKING:
    import queue
    from asyncio.futures import Future
    from logging import LogRecord


async def create_example_process_tasks(executor: ProcessTaskPoolExecutor) -> list[Future[str]]:
    """Creates example process tasks."""
    futures: list[Future[str]] = []
    for task_id in range(10):
        futures.append(executor.create_process_task(process_cpu_bound, task_id))
        # In case of new window in Windows, this method seems to occupy CPU resource in case when without sleep.
        # Otherwise, this method never releases CPU resource until all of CPU bound process finish.
        # Reason: This process may runs as asyncio task that cannot log by logger.
        print("Sleep")  # noqa: T201
        await asyncio.sleep(0.001)
    return futures


async def example_use_case(
    queue_logger: queue.Queue[LogRecord] | None = None,
    configurer: Callable[[], Any] | None = None,
) -> list[str]:
    """The example use case of ProcessTaskPoolExecutor for E2E testing."""
    with ProcessTaskPoolExecutor(
        max_workers=3,
        cancel_tasks_when_shutdown=True,
        queue=queue_logger,
        configurer=configurer,
    ) as executor:
        futures = await create_example_process_tasks(executor)
        return await asyncio.gather(*futures)


def example_use_case_method(queue_logger: queue.Queue[LogRecord] | None = None) -> Generator[str, None, None]:
    with ProcessTaskPoolExecutor(max_workers=3, cancel_tasks_when_shutdown=True, queue=queue_logger) as executor:
        futures = [executor.create_process_task(process_cpu_bound, x) for x in range(10)]
        FutureWaiter.wait(futures)
        return (future.result() for future in futures)


def example_use_case_cancel_repost_process_id(
    queue_sub: queue.Queue[LogRecord] | None = None,
    queue_main: queue.Queue[LogRecord] | None = None,
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
