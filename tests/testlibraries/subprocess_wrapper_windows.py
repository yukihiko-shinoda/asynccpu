"""Subprocess wrapper for Windows."""
import time

from tests.testlibraries import SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.keyboard_interrupter import KeyboardInterrupter


async def get_process_id():
    print("Await sleep")
    time.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
    print("Kill all processes in this window.")
    return 0


if __name__ == "__main__":
    try:
        KeyboardInterrupter(get_process_id()).test_keyboard_interrupt()
    except KeyboardInterrupt:
        time.sleep(10)
