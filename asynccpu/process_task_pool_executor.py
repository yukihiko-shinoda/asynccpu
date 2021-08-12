"""Process task pool executor."""
from __future__ import annotations

import asyncio
import sys
import threading
import weakref
from asyncio.futures import Future
from concurrent.futures import ProcessPoolExecutor
from logging import Logger, getLogger, handlers
from multiprocessing.managers import SyncManager
from typing import Dict, Literal, cast

from asynccpu.process_task import ProcessTask
from asynccpu.subprocess import ProcessForWeakSet, run

__all__ = ["ProcessTaskPoolExecutor"]


def set_queue_handler(queue) -> Logger:
    """Sets queue handler."""
    logger = getLogger()
    handler = handlers.QueueHandler(queue)
    logger.addHandler(handler)
    return logger


class ProcessTaskPoolExecutor(ProcessPoolExecutor):
    """
    see:
      - Answer: What's the correct way to clean up after an interrupted event loop?
        https://stackoverflow.com/a/30766124/12721873
        https://stackoverflow.com/a/58532304/12721873
    """

    # Reason: Assuming a general use case, method create_process_task() will not take so much than 1 second.
    TIMEOUT_IN_EMERGENCY_DEFAULT = 1

    def __init__(
        self,
        max_workers=None,
        mp_context=None,
        initializer=None,
        initargs=(),
        *,
        cancel_tasks_when_shutdown: bool = False,
        queue=None,
        configurer=None
    ) -> None:
        super().__init__(max_workers, mp_context, initializer, initargs)
        self.cancel_tasks_when_shutdown = cancel_tasks_when_shutdown
        # This SyncManager is to use Queue to receive process id from child process.
        # It's danger to instantiate by with statement around code to create child process.
        # It increases the probability hitting signal during instantiating SyncManager.
        # If it happens, Python hangs up!
        #
        # stack trace:
        # KeyboardInterrupt
        # File "/xxxx/xxxx.py", line xx, in create
        #   with SyncManager() as manager:
        # File "/usr/local/lib/python3.9/multiprocessing/managers.py", line 635, in __enter__
        #   self.start()
        # File "/usr/local/lib/python3.9/multiprocessing/managers.py", line 557, in start
        #   self._address = reader.recv()
        # File "/usr/local/lib/python3.9/multiprocessing/connection.py", line 255, in recv
        #   buf = self._recv_bytes()
        # File "/usr/local/lib/python3.9/multiprocessing/connection.py", line 419, in _recv_bytes
        #   buf = self._recv(4)
        # File "/usr/local/lib/python3.9/multiprocessing/connection.py", line 384, in _recv
        #   chunk = read(handle, remaining)
        self.sync_manager = SyncManager()
        # Reason:
        # We can't use with statement without contextlib.
        # It's better to divide __enter__() and __exit__() for simplicity and testability.
        # pylint: disable=consider-using-with
        self.sync_manager.start()
        # When use list, hash seems to be updated when check in parent process side (due to pickle?)
        # > assert list_process[0].id == process.id
        # > assert list_process[0].__hash__ == process.__hash__
        # E   assert <bound method...7fc75e20f880>> == <bound method...7fc75e20f850>>
        # E     +<bound method ProcessForWeakSet.__hash__ of
        # E        <asynccpu.subprocess.ProcessForWeakSet object at 0x7fc75e20f880>>
        # E     -<bound method ProcessForWeakSet.__hash__ of
        # E        <asynccpu.subprocess.ProcessForWeakSet object at 0x7fc75e20f850>>
        self.dictionary_process: Dict[int, ProcessForWeakSet] = self.sync_manager.dict()
        self.loop = asyncio.get_event_loop()
        self.weak_key_dictionary_process: weakref.WeakKeyDictionary[
            ProcessForWeakSet, ProcessTask
        ] = weakref.WeakKeyDictionary()
        self.lock_for_dictionary_process_task = threading.Lock()
        self.queue = queue
        self.configurer = configurer
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
        with self.lock_for_dictionary_process_task:
            for process_task in self.weak_key_dictionary_process.values():
                process_task.cancel_if_not_cancelled()
        self.shutdown(True, cancel_futures=self.cancel_tasks_when_shutdown)
        self.logger.debug("Exit ProcessTaskPoolExecutor: Finish")
        return False

    def shutdown(self, wait=True, *, cancel_futures=None):
        """
        Although ProcessPoolExecutor won't cancel any futures that are completed or running
        even if *cancel_futures* is `True`,
        This class attempt to cancel also them when *cancel_futures* is `True`.
        """
        if cancel_futures:
            self.logger.debug("Shutdown ProcessTaskPoolExecutor: Cancel all process tasks")
            self.lock_and_cancel_if_not_cancelled()
        self.logger.debug("Shutdown ProcessTaskPoolExecutor: Shutdown sync manager")
        self.sync_manager.shutdown()
        if cancel_futures is None:
            cancel_futures = self.cancel_tasks_when_shutdown
        if sys.version_info.major < 3 or sys.version_info.major == 3 and sys.version_info.minor <= 8:
            super().shutdown(wait)  # pragma: no cover
        else:
            # Reason: mypy bug
            super().shutdown(wait, cancel_futures=cancel_futures)  # type: ignore

    def lock_and_cancel_if_not_cancelled(self) -> None:
        """Cancels task like future if its not cancelled."""
        self.logger.debug("Lock and cancel if not cancelled: Start")
        # Reason: requires to set timeout. pylint: disable=consider-using-with
        is_locked = self.lock_for_dictionary_process_task.acquire(timeout=self.TIMEOUT_IN_EMERGENCY_DEFAULT)
        self.logger.debug(
            "Lock and cancel if not cancelled: Locked"
            if is_locked
            else "Lock and cancel if not cancelled: Timed out to acquire lock"
        )
        self.cancel_if_not_cancelled()
        self.logger.debug("Lock and cancel if not cancelled: Finish")

    def cancel_if_not_cancelled(self) -> None:
        self.logger.debug("Number of running process task: %d", len(self.weak_key_dictionary_process))
        for process_task in self.weak_key_dictionary_process.values():
            self.logger.debug("Cancel if not cancelled: Start")
            process_task.cancel_if_not_cancelled()
            self.logger.debug("Cancel if not cancelled: Finish")

    def create_process_task(self, function_coroutine, *args) -> Future:
        """Creates task like future by wraping coroutine."""
        with self.lock_for_dictionary_process_task:
            queue_process_id = self.sync_manager.Queue()
            task = cast(
                Future,
                self.loop.run_in_executor(
                    self,
                    run,
                    self.dictionary_process,
                    queue_process_id,
                    self.queue,
                    self.configurer,
                    function_coroutine,
                    *args
                ),
            )
            process_task = ProcessTask(queue_process_id.get(), task)
            self.weak_key_dictionary_process[process_task.process_for_week_set] = process_task
            return process_task.task
