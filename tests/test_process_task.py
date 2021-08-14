"""Test for process_task.py."""
import asyncio
from asyncio.events import get_event_loop
from asyncio.exceptions import CancelledError

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from asyncio.futures import Future
from concurrent.futures.process import ProcessPoolExecutor
from signal import SIGTERM

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from typing import Any, Type, cast

import pytest

from asynccpu.process_task import ProcessTask
from asynccpu.subprocess import ProcessForWeakSet
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.cpu_bound import cpu_bound
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket


class TestProcessTask:
    """Test for ProcessTask."""

    @pytest.mark.asyncio
    async def test_send_signal(self) -> None:
        """Process task should be able to terminate by method send_signal()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            process_task = await self.execute_test(future, SIGTERM, False, Terminated)
        assert process_task.task.done()

    @pytest.mark.asyncio
    async def test_send_signal_cancelled_future(self) -> None:
        """Process task should be able to terminate by method send_signal()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            assert future.cancel()
            process_task = await self.execute_test(future, SIGTERM, True, CancelledError)
        assert process_task.task.done()

    @staticmethod
    async def execute_test(
        future: "Future[Any]", signal_number: int, expect: bool, expect_type_error: Type[BaseException]
    ) -> ProcessTask:
        """Executes test."""
        process_task = ProcessTask(ProcessForWeakSet(int(LocalSocket.receive())), future)
        assert process_task.task.done() == expect
        assert process_task.task.cancelled() == expect
        await asyncio.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        with pytest.raises(expect_type_error):
            process_task.send_signal(signal_number)
            await process_task.task
        return process_task

    @staticmethod
    def create_future(executor: ProcessPoolExecutor) -> "Future[Any]":
        return cast("Future[Any]", get_event_loop().run_in_executor(executor, cpu_bound, 1, True))
