"""Assert log."""

from __future__ import annotations

from logging import DEBUG
from logging import INFO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import queue
    from logging import LogRecord


def assert_log(queue_logger: queue.Queue[LogRecord], *, expect_info: bool, expect_debug: bool) -> None:
    record_checker = RecordChecker()
    while not queue_logger.empty():
        record_checker.categorize(queue_logger.get())
    assert record_checker.is_output_info == expect_info
    assert record_checker.is_output_debug == expect_debug


class RecordChecker:
    """Checks log records."""

    def __init__(self) -> None:
        self.is_output_info = False
        self.is_output_debug = False

    def categorize(self, log_record: LogRecord) -> None:
        if log_record.levelno == INFO and log_record.message == "CPU-bound: Start":
            self.is_output_info = True
        if log_record.levelno == DEBUG and log_record.message == "CPU-bound: Finish":
            self.is_output_debug = True
