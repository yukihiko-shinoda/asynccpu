"""Test for process_task.py."""

from __future__ import annotations

import asyncio
import sys
from asyncio.events import get_event_loop
from asyncio.exceptions import CancelledError
from concurrent.futures.process import ProcessPoolExecutor
from signal import SIGTERM
from typing import TYPE_CHECKING
from typing import Any

import pytest

from asynccpu.process_task import ProcessTask
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.cpu_bound import cpu_bound
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket

if TYPE_CHECKING:
    from asyncio.futures import Future


class TestProcessTask:
    """Test for ProcessTask."""

    @staticmethod
    def test_hash() -> None:
        process1 = ProcessTask(1)
        process2 = ProcessTask(1)
        list_process = [process1]
        assert hash(list_process[0]) == hash(process1)
        assert hash(list_process[0]) == hash(process2)

    @staticmethod
    def test_hashable() -> None:
        process1 = ProcessTask(1)
        process2 = ProcessTask(1)
        list_process = [process1]
        assert list_process[0] == process1
        assert list_process[0] != process2

    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #       https://bugs.python.org/issue26350
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    async def test_send_signal(self) -> None:
        """Process task should be able to terminate by method send_signal()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            await self.execute_test(future, SIGTERM, expect=False, expect_type_error=Terminated)
        assert future.done()

    @pytest.mark.asyncio
    async def test_send_signal_cancelled_future(self) -> None:
        """Process task should be able to terminate by method send_signal()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            assert future.cancel()
            await self.execute_test(future, SIGTERM, expect=True, expect_type_error=CancelledError)
        assert future.done()

    @staticmethod
    async def execute_test(
        future: Future[Any],
        signal_number: int,
        *,
        expect: bool,
        expect_type_error: type[BaseException],
    ) -> None:
        """Executes test."""
        process_task = ProcessTask(int(LocalSocket.receive()))
        assert future.done() == expect
        assert future.cancelled() == expect
        await asyncio.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        process_task.send_signal(signal_number)
        with pytest.raises(expect_type_error):
            await future

    @staticmethod
    def create_future(executor: ProcessPoolExecutor) -> Future[Any]:
        # Reason: Function doesn't support kwargs.
        return get_event_loop().run_in_executor(executor, cpu_bound, 1, True)  # noqa: FBT003
