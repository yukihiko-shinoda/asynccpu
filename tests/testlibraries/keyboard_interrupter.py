"""To keep task property even raise KeyboardInterrupt."""
import asyncio
import os
import signal
import time
from asyncio.tasks import Task
from typing import Awaitable, Optional

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_MIDDLE
from tests.testlibraries.example_use_case import example_use_case_cancel
from tests.testlibraries.local_socket import LocalSocket


class KeyboardInterrupter:
    """To keep task property even raise KeyboardInterrupt."""

    def __init__(self, get_process_id: Awaitable[int]) -> None:
        # Reason: pytest bug. pylint: disable=unsubscriptable-object
        self.task: Optional[Task] = None
        self.get_process_id = get_process_id

    def test_keyboard_interrupt(self) -> None:
        """Tests keyboard interrupt and send response to pytest by socket when succeed."""
        try:
            asyncio.run(self.keyboard_interrupt())
        except KeyboardInterrupt:
            print("Sleep in except")
            time.sleep(SECOND_SLEEP_FOR_TEST_MIDDLE)
            print("Assert in except")
            assert self.task is not None
            assert self.task.done()
            assert self.task.cancelled()
            LocalSocket.send("Test succeed")
            raise

    async def keyboard_interrupt(self) -> None:
        """Simulates keyboard interrupt by CTRL_C_EVENT."""
        print("Create task")
        self.task = asyncio.create_task(example_use_case_cancel())
        process_id = await self.get_process_id
        try:
            # Reason: only for Windows. pylint: disable=no-member
            os.kill(process_id, signal.CTRL_C_EVENT)  # type: ignore
            print("Await task")
            await self.task
        except KeyboardInterrupt:
            print("Await task in except")
            # await self.task
            print("Assert")
            assert not self.task.done()
            print("Task not done")
            assert not self.task.cancelled()
            print("Task cancelled")
            raise
