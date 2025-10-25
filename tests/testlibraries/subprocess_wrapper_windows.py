"""Subprocess wrapper for Windows."""

import asyncio
from logging import getLogger

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW
from tests.testlibraries.keyboard_interrupter import TestingKeyboardInterrupt


async def wait_for_starting_process() -> int:
    logger = getLogger(__name__)
    logger.debug("Await sleep")
    await asyncio.sleep(SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW)
    logger.debug("Kill all processes in this window.")
    return 0


if __name__ == "__main__":
    TestingKeyboardInterrupt(wait_for_starting_process()).execute_test_and_report_result_to_pytest_process()
