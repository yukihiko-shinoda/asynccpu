"""To keep task property even raise KeyboardInterrupt."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import traceback
from logging import DEBUG
from logging import getLogger
from multiprocessing import Manager
from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable

from tests.testlibraries.example_use_case import example_use_case
from tests.testlibraries.local_socket import LocalSocket

if TYPE_CHECKING:
    import queue
    from collections.abc import Coroutine
    from logging import LogRecord


class ExampleUseCaseForTesting:
    """The example use case tester of ProcessTaskPoolExecutor for E2E testing in case of cancel."""

    def __init__(self) -> None:
        self.manager = Manager()
        self.queue_logger: queue.Queue[LogRecord] = self.manager.Queue(-1)
        self.coroutine = example_use_case(queue_logger=self.queue_logger, configurer=self.set_log_level_as_debug())

    @staticmethod
    def set_log_level_as_debug() -> None:
        root_logger = getLogger()
        root_logger.setLevel(DEBUG)

    async def await_and_raise(self) -> None:
        """The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
        await self.coroutine
        msg = "Keyboard interrupt isn't received."
        raise AssertionError(msg)

    def expected_log_exists(self) -> bool:
        """Checks expected log exists or not.

        Returns:
            True: Expected log exists.
            False: Expected log does not exist.
        """
        while not self.queue_logger.empty():
            message = self.queue_logger.get().message
            # Reason: This process runs as asyncio task that cannot log by logger.
            print(message)  # noqa: T201
            if message == "CPU-bound: KeyboardInterrupt":
                return True
        return False


class AsyncioEventLoopForTestingKeyboardInterrupt:
    """To keep task property even raise KeyboardInterrupt."""

    def __init__(
        self,
        target_process: Coroutine[Any, Any, Any],
        awaitable_starting_target_process: Awaitable[int],
    ) -> None:
        self.target_process = target_process
        self.awaitable_starting_target_process = awaitable_starting_target_process
        self.logger = getLogger(__name__)

    def test_keyboard_interrupt(self) -> None:
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self.start_target_process_and_interrupt_it())

    async def start_target_process_and_interrupt_it(self) -> None:
        """Simulates keyboard interrupt by CTRL_C_EVENT."""
        self.logger.debug("Create task")
        task = asyncio.create_task(self.target_process)
        process_id = await self.awaitable_starting_target_process
        # Reason: only for Windows. pylint: disable=no-member
        os.kill(process_id, signal.CTRL_C_EVENT)  # type: ignore[attr-defined]
        self.logger.debug("Await task")
        await task


class TestingKeyboardInterrupt:
    """To test keyboard interrupt."""

    def __init__(self, awaitable_starting_process: Awaitable[int]) -> None:
        self.example_use_case_for_testing = ExampleUseCaseForTesting()
        self.asyncio_event_loop_for_testing_keyboard_interrupt = AsyncioEventLoopForTestingKeyboardInterrupt(
            self.example_use_case_for_testing.await_and_raise(),
            awaitable_starting_process,
        )
        self.logger = getLogger(__name__)

    def execute_test_and_report_result_to_pytest_process(self) -> None:
        """Tests keyboard interrupt and send response to pytest by socket when succeed."""
        try:
            self.execute_test()
        except BaseException:
            # To send result to pytest even if unexpected error occurred.
            self.logger.exception("Unexpected error occurred")
            traceback.print_exc()
            LocalSocket.send("Test failed")
            raise
        else:
            LocalSocket.send("Test succeed")
        finally:
            asyncio.run(asyncio.sleep(10))

    def execute_test(self) -> None:
        self.asyncio_event_loop_for_testing_keyboard_interrupt.test_keyboard_interrupt()
        if not self.example_use_case_for_testing.expected_log_exists():
            msg = "Expected log does not exist."
            raise AssertionError(msg)
