"""Test for process_task.py."""
from asyncio.events import get_event_loop
from asyncio.exceptions import CancelledError

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from asyncio.futures import Future
from concurrent.futures.process import ProcessPoolExecutor

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from typing import Any, cast

import pytest

from asynccpu.process_task import ProcessTask
from asynccpu.subprocess import ProcessForWeakSet
from tests.testlibraries.cpu_bound import cpu_bound
from tests.testlibraries.local_socket import LocalSocket


class TestProcessTask:
    """Test for ProcessTask."""

    @pytest.mark.asyncio
    async def test_cancel_if_not_cancelled(self) -> None:
        """Process task should be able to cancel by method cancel_if_not_cancelled()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            process_task = await self.execute_test(future, False)
        assert process_task.task.cancelled()
        assert process_task.task.done()

    @pytest.mark.asyncio
    async def test_cancel_if_not_cancelled_cancelled_future(self) -> None:
        """Process task should be able to cancel by method cancel_if_not_cancelled()."""
        with ProcessPoolExecutor() as executor:
            future = self.create_future(executor)
            assert future.cancel()
            process_task = await self.execute_test(future, True)
        assert process_task.task.cancelled()
        assert process_task.task.done()

    @staticmethod
    async def execute_test(future: "Future[Any]", expect: bool) -> ProcessTask:
        """Executes test."""
        process_task = ProcessTask(ProcessForWeakSet(int(LocalSocket.receive())), future)
        assert process_task.task.done() == expect
        assert process_task.task.cancelled() == expect
        with pytest.raises(CancelledError):
            process_task.cancel_if_not_cancelled()
            await process_task.task
        return process_task

    @staticmethod
    def create_future(executor: ProcessPoolExecutor) -> "Future[Any]":
        return cast("Future[Any]", get_event_loop().run_in_executor(executor, cpu_bound, 1, True))
