"""Test of keyboard Interrupt for Windows."""

import asyncio
from logging import getLogger

# Reason: only for Windows. pylint: disable=import-error
import win32api  # type: ignore[import-untyped]

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW
from tests.testlibraries.keyboard_interrupter import TestingKeyboardInterrupt
from tests.testlibraries.local_socket import LocalSocket

win32api.SetConsoleCtrlHandler(None, bAdd=False)


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
