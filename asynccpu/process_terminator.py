"""see:

- Answer: multiprocess - Python: concurrent.futures How to make it cancelable? - Stack Overflow
https://stackoverflow.com/a/45515052/12721873
"""

from __future__ import annotations

from logging import getLogger

import psutil


class ProcessTerminator:
    """Process terminator.

    Designed to reduce if statement.
    """

    def __init__(self, *, force: bool = False) -> None:
        self.execute = self.kill if force else self.terminate

    @staticmethod
    def kill(process: psutil.Process) -> None:
        process.kill()

    @staticmethod
    def terminate(process: psutil.Process) -> None:
        process.terminate()


def terminate_descendant_processes(parent_pid: int, *, force: bool = False) -> None:
    """Terminates descendant processes.

    This method doesn't have parameter for sending signal since psutil seems to being black box the difference between
    Linux and Windows.
    """
    logger = getLogger(__name__)
    process_terminator = ProcessTerminator(force=force)
    parent = psutil.Process(parent_pid)
    children: list[psutil.Process] = parent.children(recursive=True)
    logger.debug("Terminate child processes")
    for process in children:
        process_terminator.execute(process)
