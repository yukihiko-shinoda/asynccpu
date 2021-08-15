"""Subprocess wrapper for Windows."""
import asyncio

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW
from tests.testlibraries.keyboard_interrupter import KeyboardInterrupter


async def get_process_id() -> int:
    print("Await sleep")
    await asyncio.sleep(SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW)
    print("Kill all processes in this window.")
    return 0


if __name__ == "__main__":
    KeyboardInterrupter(get_process_id()).test_keyboard_interrupt()
