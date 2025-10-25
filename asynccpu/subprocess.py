"""Subprocess."""

from __future__ import annotations

import asyncio
import os
from logging import Logger
from logging import getLogger
from logging import handlers
from signal import SIGTERM
from signal import signal
from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Literal

from asynccpu.process_task import ProcessTask
from asynccpu.process_terminator import terminate_descendant_processes

if TYPE_CHECKING:
    import queue
    from asyncio.events import AbstractEventLoop
    from logging import LogRecord
    from multiprocessing.managers import DictProxy
    from types import FrameType
    from types import TracebackType

    from asynccpu.types import ParamSpecCoroutineFunctionArguments
    from asynccpu.types import TypeVarReturnValue


class Replier:
    """To reply current process status to parent process."""

    def __init__(
        self,
        dictionary_process: DictProxy[int, ProcessTask],
        queue_process_id: queue.Queue[ProcessTask],
    ) -> None:
        self.dictionary_process = dictionary_process
        self.queue_process_id = queue_process_id
        self.process_id: int | None = None
        self.logger = getLogger(__name__)

    def __enter__(self) -> None:
        self.process_id = os.getpid()
        process_for_weak_set = ProcessTask(self.process_id)
        self.dictionary_process[self.process_id] = process_for_weak_set
        self.queue_process_id.put(process_for_weak_set)

    # Reason: pylint bug. pylint: disable=unsubscriptable-object
    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Terminates current subprocess."""
        if not self.process_id:
            # Reason: Difficult to aim to stop before set process id.
            return False  # pragma: no cover
        try:
            self.logger.debug("len(self.dictionary_process): %d", len(self.dictionary_process))
            self.dictionary_process.pop(self.process_id, None)
        except (ValueError, BrokenPipeError):
            self.logger.exception("Unexpected error occurred")
        self.logger.debug("Finish run coroutine")
        return False


class LoggingInitializer:
    """Initializes logging settings for subprocess."""

    def __init__(
        self,
        queue_logger: queue.Queue[LogRecord] | None = None,
        configurer: Callable[[], Any] | None = None,
    ) -> None:
        self.queue_logger = queue_logger
        self.configurer = configurer

    def init(self) -> None:
        if self.queue_logger:
            self.set_queue_handler(self.queue_logger)
        if self.configurer:
            self.configurer()

    @staticmethod
    def set_queue_handler(queue_logger: queue.Queue[LogRecord]) -> Logger:
        logger = getLogger()
        handler = handlers.QueueHandler(queue_logger)
        logger.addHandler(handler)
        return logger


def run(
    replier: Replier,
    logging_initializer: LoggingInitializer | None,
    corofn: Callable[ParamSpecCoroutineFunctionArguments, Awaitable[TypeVarReturnValue]],
    *args: ParamSpecCoroutineFunctionArguments.args,
    **kwargs: ParamSpecCoroutineFunctionArguments.kwargs,
) -> TypeVarReturnValue:
    """Runs a coroutine in a new event loop.

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

    def sigterm_handler(_signum: int, _frame: FrameType | None) -> None:
        # Reason: Testing in Subprocess noqa: ERA001
        cancel_coroutine(logger)  # pragma: no cover

    signal(SIGTERM, sigterm_handler)
    with replier:
        try:
            loop = asyncio.new_event_loop()
            coro = corofn(*args, **kwargs)
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        # Reason: Testing in Subprocess noqa: ERA001
        except KeyboardInterrupt:  # pragma: no cover
            cancel_coroutine(logger)
            raise
        finally:
            close_if_has_created(loop)


def close_if_has_created(loop: AbstractEventLoop | None) -> None:
    if loop is not None:
        loop.close()


def cancel_coroutine(logger: Logger) -> None:
    """Since this process takes next coroutine and execute it even if succeed to cancel current coroutine.

    see:
      - Answer: multiprocess - Python: concurrent.futures How to make it cancelable? - Stack Overflow
        https://stackoverflow.com/a/45515052/12721873
    """
    logger.info("Cancel run coroutine")
    terminate_descendant_processes(os.getpid())
