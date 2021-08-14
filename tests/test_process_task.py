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
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.cpu_bound import cpu_bound
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket


class TestProcessTask:
    """Test for ProcessTask."""

    @staticmethod
    def test_hash() -> None:
        process1 = ProcessTask(1)
        process2 = ProcessTask(1)
        list_process = [process1]
        assert list_process[0].__hash__() == process1.__hash__()
        assert list_process[0].__hash__() == process2.__hash__()

    @staticmethod
    def test_hashable() -> None:
        process1 = ProcessTask(1)
        process2 = ProcessTask(1)
        list_process = [process1]
        assert list_process[0] == process1
        assert list_process[0] != process2

    @pytest.mark.asyncio
    async def test_send_signal(self) -> None:
        """Process task should be able to terminate by method send_signal()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            await self.execute_test(future, SIGTERM, False, Terminated)
        assert future.done()

    @pytest.mark.asyncio
    async def test_send_signal_cancelled_future(self) -> None:
        """Process task should be able to terminate by method send_signal()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            assert future.cancel()
            await self.execute_test(future, SIGTERM, True, CancelledError)
        assert future.done()

    @staticmethod
    async def execute_test(
        future: "Future[Any]", signal_number: int, expect: bool, expect_type_error: Type[BaseException]
    ) -> None:
        """Executes test."""
        process_task = ProcessTask(int(LocalSocket.receive()))
        assert future.done() == expect
        assert future.cancelled() == expect
        await asyncio.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        with pytest.raises(expect_type_error):
            process_task.send_signal(signal_number)
            await future

    @staticmethod
    def create_future(executor: ProcessPoolExecutor) -> "Future[Any]":
        return cast("Future[Any]", get_event_loop().run_in_executor(executor, cpu_bound, 1, True))
