"""Process task pool executor."""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import weakref
from asyncio.futures import Future
from concurrent.futures import ProcessPoolExecutor
from logging import getLogger
from typing import Awaitable, Callable, Literal, cast

import psutil

__all__ = ["ProcessTaskPoolExecutor"]


def run(corofn: Callable[..., Awaitable], *args):
    """
    This function requires to be orphaned since ProcecssPoolExecutor requires picklable.
    The argument of Coroutine requires not "raw Corutine object" but "Coroutine function"
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
    logger = getLogger(__name__)
    logger.debug("Start run coroutine")
    loop = asyncio.new_event_loop()
    try:
        coro = corofn(*args)
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except KeyboardInterrupt:  # pragma: no cover
        logger.info("Cancel run coroutine")
        # Since this process takes next coroutine and execute it
        # even if succeed to cancel current coroutine.
        # see:
        #   - Answer: multiprocess - Python: concurrent.futures How to make it cancelable? - Stack Overflow
        #     https://stackoverflow.com/a/45515052/12721873
        terminate_processes(os.getpid())
        raise
    finally:
        loop.close()
        logger.debug("Finish run coroutine")


def terminate_processes(parent_pid: int, *, force: bool = False):
    """
    This method doesn't have parameter for sending signal
    since psutil seems to being blackbox the difference between Linux and Windows.
    see:
      - Answer: multiprocess - Python: concurrent.futures How to make it cancelable? - Stack Overflow
        https://stackoverflow.com/a/45515052/12721873
    """
    logger = getLogger(__name__)
    parent = psutil.Process(parent_pid)
    children = parent.children(recursive=True)
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


class ProcessTaskPoolExecutor(ProcessPoolExecutor):
    """
    see:
      - Answer: What's the correct way to clean up after an interrupted event loop?
        https://stackoverflow.com/a/30766124/12721873
        https://stackoverflow.com/a/58532304/12721873
    """

    def __init__(
        self,
        max_workers=None,
        mp_context=None,
        initializer=None,
        initargs=(),
        *,
        cancel_tasks_when_shutdown: bool = False
    ) -> None:
        super().__init__(max_workers, mp_context, initializer, initargs)
        self.cancel_tasks_when_shutdown = cancel_tasks_when_shutdown
        self.loop = asyncio.get_event_loop()
        self.list_process_task: weakref.WeakSet[Future] = weakref.WeakSet()
        self.lock_for_list_process_task = threading.Lock()
        self.logger = getLogger(__name__)

    def __enter__(self) -> ProcessTaskPoolExecutor:
        # pylint can't detect following cast:
        # return cast(ProcessTaskPoolExecutor, super().__enter__())
        return self

    # Reason: pylint bug. pylint: disable=unsubscriptable-object
    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
        self.logger.debug("Exit ProcessTaskPoolExecutor: Start")
        self.logger.debug("exc_type = %s", exc_type)
        self.logger.debug("Exit ProcessTaskPoolExecutor: Cancelled all process tasks")
        with self.lock_for_list_process_task:
            for task in self.list_process_task:
                self.cancel_if_not_cancelled(task)
        self.shutdown()
        self.logger.debug("Exit ProcessTaskPoolExecutor: Finish")
        return False

    def shutdown(self, wait=True, *, cancel_futures=None):
        if cancel_futures is None:
            cancel_futures = self.cancel_tasks_when_shutdown
        if sys.version_info.major < 3 or sys.version_info.major == 3 and sys.version_info.minor <= 8:
            super().shutdown(wait)  # pragma: no cover
        else:
            # Reason: mypy bug
            super().shutdown(wait, cancel_futures=cancel_futures)  # type: ignore

    def cancel_if_not_cancelled(self, task: Future) -> None:
        """Cancels task like future if its not cancelled."""
        self.logger.debug(task)
        cancelled = task.cancelled()
        self.logger.debug("Cancelled?: %s", cancelled)
        if cancelled:
            return
        cancel = task.cancel()
        self.logger.debug("Cancel succeed?: %s", cancel)

    def create_process_task(self, function_coroutine, *args) -> Future:
        """Creates task like future by wraping coroutine."""
        with self.lock_for_list_process_task:
            task = cast(Future, self.loop.run_in_executor(self, run, function_coroutine, *args))
            self.list_process_task.add(task)
            self.list_process_task = self.garbage_collect(self.list_process_task)
            return task

    @staticmethod
    def garbage_collect(list_process_task: weakref.WeakSet) -> weakref.WeakSet:
        new_list_process_task: weakref.WeakSet[Future] = weakref.WeakSet()
        for process_task in list(list_process_task):
            if not process_task.done():
                new_list_process_task.add(process_task)
        return new_list_process_task
