"""Subprocess."""
import asyncio
import os
import queue
from asyncio.events import AbstractEventLoop
from logging import Logger, LogRecord, getLogger, handlers
from signal import SIGTERM, signal
from typing import Any, Awaitable, Callable, Dict, List, Optional

import psutil

from asynccpu.types import TypeVarReturnValue


class ProcessForWeakSet:
    """
    Requirement of this class:
    - Picklable to set SyncManager.list()
      object is not picklable
    - Hashable to use key of weakset:
      TypeError: unhashable type
      see:
        Answer: python - Using an object's id() as a hash value - Stack Overflow
        https://stackoverflow.com/a/55086062/12721873
        Answer: python - What makes a user-defined class unhashable? - Stack Overflow
        https://stackoverflow.com/a/29434112/12721873
        Answer: python - How can I make class properties immutable? - Stack Overflow
        https://stackoverflow.com/a/43486647/12721873
    Since psutil.Process is not picklable.
    """

    def __init__(self, process_id: int) -> None:
        self._id = (process_id,)

    @property
    # Reason: It's no problem to consider that "id" is snake_case. pylint: disable=invalid-name
    def id(self) -> int:
        return self._id[0]

    def __hash__(self) -> int:
        return hash(self._id)


def set_queue_handler(queue_logger: queue.Queue[LogRecord]) -> Logger:
    """Sets queue handler."""
    logger = getLogger()
    handler = handlers.QueueHandler(queue_logger)
    logger.addHandler(handler)
    return logger


def run(
    dictionary_process: Dict[int, ProcessForWeakSet],
    queue_process_id: queue.Queue[ProcessForWeakSet],
    queue_logger: queue.Queue[LogRecord],
    configurer: Optional[Callable[[], Any]],
    corofn: Callable[..., Awaitable[TypeVarReturnValue]],
    *args: Any
) -> TypeVarReturnValue:
    """
    This function requires to be orphaned since ProcessPoolExecutor requires picklable.
    The argument of Coroutine requires not "raw Coroutine object" but "Coroutine function"
    since raw Coroutine object is not picklable:
      TypeError: cannot pickle 'coroutine' object
    see:
      - multiprocessing — Process-based parallelism
        https://docs.python.org/3/library/multiprocessing.html
      - Answer: Python multiprocessing PicklingError: Can't pickle <type 'function'> - Stack Overflow
        https://stackoverflow.com/a/8805244/12721873
      - Answer: Why coroutines cannot be used with run_in_executor? - Stack Overflow
        https://stackoverflow.com/a/46075571/12721873
    """
    if queue_logger is not None:
        set_queue_handler(queue_logger)
    if configurer is not None:
        configurer()
    logger = getLogger(__name__)
    logger.debug("Start run coroutine")

    def sigterm_handler(_signum: int, _frame: Optional[Any]) -> None:
        # Reason: Testing in Subprocess
        cancel_coroutine(logger)  # pragma: no cover

    signal(SIGTERM, sigterm_handler)
    prosess_id = os.getpid()
    process_for_weak_set = ProcessForWeakSet(prosess_id)
    try:
        dictionary_process[prosess_id] = process_for_weak_set
        queue_process_id.put(process_for_weak_set)
        loop = asyncio.new_event_loop()
        coro = corofn(*args)
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    # Reason: Testing in Subprocess
    except KeyboardInterrupt:  # pragma: no cover
        cancel_coroutine(logger)
        raise
    finally:
        terminate(loop, logger, dictionary_process, prosess_id)


def terminate(
    loop: Optional[AbstractEventLoop], logger: Logger, dictionary_process: Dict[int, ProcessForWeakSet], pid: int
) -> None:
    """Terminates current subprocess."""
    if loop is not None:
        loop.close()
    try:
        logger.debug("len(list_process): %d", len(dictionary_process))
        dictionary_process.pop(pid, None)
        # # Following:
        # # RecursionError: maximum recursion depth exceeded
        # list_process.remove(process_for_weak_set)
    except (ValueError, BrokenPipeError) as error:
        logger.exception("%s", error)
    logger.debug("Finish run coroutine")


def cancel_coroutine(logger: Logger) -> None:
    """
    Since this process takes next coroutine and execute it
    even if succeed to cancel current coroutine.
    see:
      - Answer: multiprocess - Python: concurrent.futures How to make it cancelable? - Stack Overflow
        https://stackoverflow.com/a/45515052/12721873
    """
    logger.info("Cancel run coroutine")
    terminate_processes(os.getpid())


def terminate_processes(parent_pid: int, *, force: bool = False) -> None:
    """
    This method doesn't have parameter for sending signal
    since psutil seems to being blackbox the difference between Linux and Windows.
    see:
      - Answer: multiprocess - Python: concurrent.futures How to make it cancelable? - Stack Overflow
        https://stackoverflow.com/a/45515052/12721873
    """
    logger = getLogger(__name__)
    parent = psutil.Process(parent_pid)
    children: List[psutil.Process] = parent.children(recursive=True)
    logger.debug("Terminate child processes")
    if force:
        for process in children:
            process.kill()
        logger.debug("Terminate target processes")
        parent.kill()
    else:
        for process in children:
            process.terminate()
        logger.debug("Terminate target processes")
        parent.terminate()