"""Subprocess."""
import asyncio
import os

# Reason: To support Python 3.8 or less pylint: disable=unused-import
import queue
from asyncio.events import AbstractEventLoop

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from logging import Logger, LogRecord, getLogger, handlers
from signal import SIGTERM, signal
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, Literal, Optional, Type

from asynccpu.process_terminator import terminate_processes
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


class Replier:
    """To reply current process status to parent process."""

    def __init__(
        self, dictionary_process: Dict[int, ProcessForWeakSet], queue_process_id: "queue.Queue[ProcessForWeakSet]"
    ) -> None:
        self.dictionary_process = dictionary_process
        self.queue_process_id = queue_process_id
        self.process_id: Optional[int] = None
        self.logger = getLogger(__name__)

    def __enter__(self) -> None:
        self.process_id = os.getpid()
        process_for_weak_set = ProcessForWeakSet(self.process_id)
        self.dictionary_process[self.process_id] = process_for_weak_set
        self.queue_process_id.put(process_for_weak_set)

    # Reason: pylint bug. pylint: disable=unsubscriptable-object
    def __exit__(
        self,
        _exc_type: Optional[Type[BaseException]],
        _exc_val: Optional[BaseException],
        _exc_tb: Optional[TracebackType],
    ) -> Literal[False]:
        """Terminates current subprocess."""
        if not self.process_id:
            # Reason: Difficult to aim to stop before set process id.
            return False  # pragma: no cover
        try:
            self.logger.debug("len(self.dictionary_process): %d", len(self.dictionary_process))
            self.dictionary_process.pop(self.process_id, None)
            # # Following:
            # # RecursionError: maximum recursion depth exceeded
            # list_process.remove(process_for_weak_set)
        except (ValueError, BrokenPipeError) as error:
            self.logger.exception("%s", error)
        self.logger.debug("Finish run coroutine")
        return False


class LoggingInitializer:
    """Initializes logging settings for subprocess."""

    def __init__(
        self, queue_logger: Optional["queue.Queue[LogRecord]"] = None, configurer: Optional[Callable[[], Any]] = None
    ) -> None:
        self.queue_logger = queue_logger
        self.configurer = configurer

    def init(self) -> None:
        if self.queue_logger:
            self.set_queue_handler(self.queue_logger)
        if self.configurer:
            self.configurer()

    @staticmethod
    def set_queue_handler(queue_logger: "queue.Queue[LogRecord]") -> Logger:
        logger = getLogger()
        handler = handlers.QueueHandler(queue_logger)
        logger.addHandler(handler)
        return logger


def run(
    replier: Replier,
    logging_initializer: Optional[LoggingInitializer],
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
    if logging_initializer:
        logging_initializer.init()
    logger = getLogger(__name__)
    logger.debug("Start run coroutine")

    def sigterm_handler(_signum: int, _frame: Optional[Any]) -> None:
        # Reason: Testing in Subprocess
        cancel_coroutine(logger)  # pragma: no cover

    signal(SIGTERM, sigterm_handler)
    with replier:
        try:
            loop = asyncio.new_event_loop()
            coro = corofn(*args)
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        # Reason: Testing in Subprocess
        except KeyboardInterrupt:  # pragma: no cover
            cancel_coroutine(logger)
            raise
        finally:
            close_if_has_created(loop)


def close_if_has_created(loop: Optional[AbstractEventLoop]) -> None:
    if loop is not None:
        loop.close()


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
