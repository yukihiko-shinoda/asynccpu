"""To keep task property even raise KeyboardInterrupt."""
import asyncio
import os

# Reason: For type hint. pylint: disable=unused-import
import queue
import signal
import traceback
from asyncio.tasks import Task

# Reason: For type hint. pylint: disable=unused-import
from logging import DEBUG, LogRecord, getLogger
from multiprocessing import Manager
from typing import Any, Awaitable, Callable, Optional

from tests.testlibraries.example_use_case import example_use_case
from tests.testlibraries.local_socket import LocalSocket


class KeyboardInterrupter:
    """To keep task property even raise KeyboardInterrupt."""

    def __init__(self, get_process_id: Awaitable[int]) -> None:
        self.get_process_id = get_process_id
        # Reason: pytest bug. pylint: disable=unsubscriptable-object
        self.task: Optional[Task[Any]] = None
        self.manager = Manager()
        self.queue_log_record: "queue.Queue[LogRecord]" = self.manager.Queue(-1)
        self.logger = getLogger(__name__)

    def test_keyboard_interrupt(self) -> None:
        """Tests keyboard interrupt and send response to pytest by socket when succeed."""
        try:
            self.test()
        except BaseException as error:
            self.logger.exception(error)
            traceback.print_exc()
            LocalSocket.send("Test failed")
            raise
        else:
            LocalSocket.send("Test succeed")
        finally:
            asyncio.run(asyncio.sleep(10))

    async def keyboard_interrupt(self) -> None:
        """Simulates keyboard interrupt by CTRL_C_EVENT."""
        print("Create task")
        coroutine = self.run_example_use_case_and_raise(self.queue_log_record, set_log_level_as_debug)
        self.task = asyncio.create_task(coroutine)
        process_id = await self.get_process_id
        # Reason: only for Windows. pylint: disable=no-member
        os.kill(process_id, signal.CTRL_C_EVENT)  # type: ignore
        print("Await task")
        await self.task

    @staticmethod
    async def run_example_use_case_and_raise(
        queue_logger: "queue.Queue[LogRecord]", worker_configurer: Optional[Callable[[], Any]]
    ) -> None:
        """The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
        await example_use_case(queue_logger=queue_logger, configurer=worker_configurer)
        raise Exception("Keyboard interrupt isn't received.")

    def test(self) -> None:
        try:
            asyncio.run(self.keyboard_interrupt())
        except KeyboardInterrupt:
            pass
        assert self.expected_log_exists(), "Expected log not found"

    def expected_log_exists(self) -> bool:
        """
        True: Expected log exists.
        False: Expected log does not exist.
        """
        while not self.queue_log_record.empty():
            message = self.queue_log_record.get().message
            print(message)
            if message == "CPU-bound: KeyboardInterupt":
                return True
        return False


def set_log_level_as_debug() -> None:
    root_logger = getLogger()
    root_logger.setLevel(DEBUG)
