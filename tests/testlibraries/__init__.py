"""Test libraries."""

SECOND_SLEEP_FOR_TEST_SHORT = 0.12
SECOND_SLEEP_FOR_TEST_MIDDLE = 0.25
# To allow all child processes to initialize when running with coverage
SECOND_SLEEP_FOR_WAITING_FOR_INITIALIZING_CHILD_PROCESS_OF_COVERAGE = 5
# New window in Windows works much slow.
SECOND_SLEEP_FOR_TEST_WINDOWS_NEW_WINDOW = 3
# When set 150, test_keyboard_interrupt_ctrl_c_popen failed in GitHub Actions.
SECOND_SLEEP_FOR_TEST_KEYBOARD_INTERRUPT_CTRL_C_POPEN_SHORT = 180
SECOND_SLEEP_FOR_TEST_KEYBOARD_INTERRUPT_CTRL_C_POPEN_MIDDLE = 180
