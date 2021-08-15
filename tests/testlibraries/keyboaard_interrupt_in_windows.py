"""Test of keyboard Interrupt for Windows."""
# Reason: only for Windows. pylint: disable=import-error
import asyncio

import win32api  # type: ignore

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW
from tests.testlibraries.keyboard_interrupter import KeyboardInterrupter
from tests.testlibraries.local_socket import LocalSocket

win32api.SetConsoleCtrlHandler(None, False)


async def get_process_id() -> int:
    print("Await socket")
    process_id = int(LocalSocket.receive())
    print("Await sleep")
    await asyncio.sleep(SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW)
    print("Kill group lead process")
    return process_id


if __name__ == "__main__":
    KeyboardInterrupter(get_process_id()).test_keyboard_interrupt()
