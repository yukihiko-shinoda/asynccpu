"""Test of keyboard Interrupt for Windows."""

import asyncio
import ctypes
from logging import getLogger

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW
from tests.testlibraries.keyboard_interrupter import TestingKeyboardInterrupt
from tests.testlibraries.local_socket import LocalSocket

# On Windows, processes created with CREATE_NEW_PROCESS_GROUP have Ctrl+C disabled by default.
# Enable Ctrl+C handling using the Windows API directly via ctypes.
# SetConsoleCtrlHandler(NULL, FALSE) enables the default Ctrl+C handling.
# Reason: ctypes.windll is only available in Windows.
ctypes.windll.kernel32.SetConsoleCtrlHandler(None, 0)  # type: ignore[attr-defined]


async def wait_for_starting_process() -> int:
    """Awaits starting process and returns its process id."""
    logger = getLogger(__name__)
    logger.debug("Await socket")
    process_id = int(LocalSocket.receive())
    logger.debug("Await sleep")
    await asyncio.sleep(SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW)
    logger.debug("Kill group lead process")
    return process_id


if __name__ == "__main__":
    TestingKeyboardInterrupt(wait_for_starting_process()).execute_test_and_report_result_to_pytest_process()
