"""Process task pool executor."""
from __future__ import annotations

import asyncio

# Reason: To support Python 3.8 or less pylint: disable=unused-import
import queue
import sys
import threading
import traceback
from asyncio.futures import Future
from concurrent.futures import ProcessPoolExecutor

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from logging import LogRecord, getLogger
from multiprocessing.context import BaseContext
from multiprocessing.managers import SyncManager
from signal import SIGTERM, getsignal, signal
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, Iterable, Literal, Optional, Tuple, Type, cast

import psutil

from asynccpu.process_task import ProcessTask
from asynccpu.subprocess import LoggingInitializer, Replier, run
from asynccpu.types import TypeVarReturnValue

__all__ = ["ProcessTaskPoolExecutor"]


class ProcessTaskFactory:
    """Factory for ProcessTask."""

    def __init__(
        self,
        process_pool_executor: ProcessPoolExecutor,
        sync_manager: SyncManager,
        *,
        logging_initializer: Optional[LoggingInitializer] = None,
    ) -> None:
        self.process_pool_executor = process_pool_executor
        self.sync_manager = sync_manager
        # When use list, hash seems to be updated when check in parent process side (due to pickle?)
        # > assert list_process[0].id == process.id
        # > assert list_process[0].__hash__ == process.__hash__
        # E   assert <bound method...7fc75e20f880>> == <bound method...7fc75e20f850>>
        # E     +<bound method ProcessForWeakSet.__hash__ of
        # E        <asynccpu.subprocess.ProcessForWeakSet object at 0x7fc75e20f880>>
        # E     -<bound method ProcessForWeakSet.__hash__ of
        # E        <asynccpu.subprocess.ProcessForWeakSet object at 0x7fc75e20f850>>
        self.dictionary_process: Dict[int, ProcessTask] = sync_manager.dict()
        self.logging_initializer = logging_initializer
        self.loop = asyncio.get_event_loop()
        self.logger = getLogger(__name__)

    def create(self, function_coroutine: Callable[..., Awaitable[Any]], *args: Any) -> "Future[Any]":
        """Creates ProcessTask."""
        queue_process_id = self.sync_manager.Queue()
        replier = Replier(self.dictionary_process, queue_process_id)
        task = cast(
            "Future[Any]",
            self.loop.run_in_executor(
                self.process_pool_executor, run, replier, self.logging_initializer, function_coroutine, *args,
            ),
        )
        try:
            queue_process_id.get()
        except BaseException as error:
            self.logger.debug("%s", error)
            self.logger.debug(task)
            cancelled = task.cancelled()
            self.logger.debug("Cancelled?: %s", cancelled)
            if cancelled:
                # Reason: This conditional raise is just in case.
                raise  # pragma: no cover
            cancel = task.cancel()
            self.logger.debug("Cancel succeed?: %s", cancel)
            raise
        return task

    def send_signal(self, signal_number: int) -> None:
        for process_task in self.items_dictionary_process():
            self.logger.debug("Send signal: Start")
            process_task.send_signal(signal_number)
            self.logger.debug("Send signal: Finish")

    def items_dictionary_process(self) -> Iterable[ProcessTask]:
        """DictProxy often returns not list but single instance when call items()"""
        items_dictionary_process = self.dictionary_process.values()
        self.logger.debug("type(items_dictionary_process)=%s", type(items_dictionary_process))
        if isinstance(items_dictionary_process, ProcessTask):
            return [items_dictionary_process]
        return items_dictionary_process


class ProcessTaskManager:
    """Process task manager."""

    # Reason: Assuming a general use case, method create_process_task() will not take so much than 1 second.
    TIMEOUT_IN_EMERGENCY_DEFAULT = 1

    def __init__(
        self, process_task_factory: ProcessTaskFactory, *, timeout_in_emergency: int = TIMEOUT_IN_EMERGENCY_DEFAULT
    ) -> None:
        """
        timeout_in_emergency: The time to force breaking lock in emergency.
        """
        self.lock_for_dictionary_process_task = threading.Lock()
        self.process_task_factory = process_task_factory
        self.timeout_in_emergency = timeout_in_emergency
        self.logger = getLogger(__name__)

    def lock_and_send_signal(self, signal_number: int) -> None:
        """Cancels task like future if its not cancelled."""
        self.logger.debug("Lock and send signal: Start")
        # Reason: requires to set timeout. pylint: disable=consider-using-with
        is_locked = self.lock_for_dictionary_process_task.acquire(timeout=self.timeout_in_emergency)
        self.logger.debug(
            "Lock and send signal: Locked" if is_locked else "Lock and send signal: Timed out to acquire lock"
        )
        self.process_task_factory.send_signal(signal_number)
        self.logger.debug("Lock and send signal: Finish")

    def create_process_task(
        self, function_coroutine: Callable[..., Awaitable[TypeVarReturnValue]], *args: Any
    ) -> "Future[TypeVarReturnValue]":
        """Creates task like future by wraping coroutine."""
        with self.lock_for_dictionary_process_task:
            return self.process_task_factory.create(function_coroutine, *args)


class ProcessTaskPoolExecutor(ProcessPoolExecutor):
    """
    see:
      - Answer: What's the correct way to clean up after an interrupted event loop?
        https://stackoverflow.com/a/30766124/12721873
        https://stackoverflow.com/a/58532304/12721873
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        mp_context: Optional[BaseContext] = None,
        initializer: Optional[Callable[..., Any]] = None,
        initargs: Tuple[Any, ...] = (),
        *,
        cancel_tasks_when_shutdown: bool = False,
        # Reason: This argument name is API. pylint: disable=redefined-outer-name
        queue: Optional["queue.Queue[LogRecord]"] = None,
        configurer: Optional[Callable[[], Any]] = None,
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
        logging_initializer = LoggingInitializer(queue, configurer)
        process_task_factory = ProcessTaskFactory(self, self.sync_manager, logging_initializer=logging_initializer)
        self.process_task_manager = ProcessTaskManager(process_task_factory)
        self.logger = getLogger(__name__)
        self.original_sigint_handler = getsignal(SIGTERM)
        signal(SIGTERM, self.sigterm_hander)

    def __enter__(self) -> ProcessTaskPoolExecutor:
        # pylint can't detect following cast:
        # return cast(ProcessTaskPoolExecutor, super().__enter__())
        super().__enter__()
        return self

    # Reason: pylint bug. pylint: disable=unsubscriptable-object
    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> Literal[False]:
        self.logger.debug("Exit ProcessTaskPoolExecutor: Start")
        self.logger.debug("exc_type = %s", exc_type)
        self.logger.debug("exc_val = %s", exc_val)
        self.logger.debug("exc_tb = %s", "".join(traceback.format_tb(exc_tb)))
        self._shutdown(True, signal_number=SIGTERM)
        # pylint can't detect that return value is False:
        # return_value = super().__exit__(exc_type, exc_val, exc_tb)
        self.logger.debug("Exit ProcessTaskPoolExecutor: Finish")
        return False

    # Reason: Can't collect coverage because of termination.
    def sigterm_hander(self, _signum: int, _frame: Optional[Any]) -> None:  # pragma: no cover
        self.logger.debug("SIGTERM handler ProcessTaskPoolExecutor: Start")
        self._shutdown(True, signal_number=SIGTERM)
        signal(SIGTERM, self.original_sigint_handler)
        self.logger.debug("SIGTERM handler ProcessTaskPoolExecutor: Finish")
        psutil.Process().terminate()
        self.logger.debug("SIGTERM handler ProcessTaskPoolExecutor: Sent SIGTERM")

    def shutdown(self, wait: bool = True, *, cancel_futures: Optional[bool] = None) -> None:
        self._shutdown(wait, cancel_futures=cancel_futures)

    def _shutdown(
        self, wait: bool = True, *, cancel_futures: Optional[bool] = None, signal_number: int = SIGTERM
    ) -> None:
        """
        Although ProcessPoolExecutor won't cancel any futures that are completed or running
        even if *cancel_futures* is `True`,
        This class attempt to cancel also them when *cancel_futures* is `True`.
        """
        if cancel_futures is None:
            cancel_futures = self.cancel_tasks_when_shutdown
        # In Windows, it should not send SIGTERM.
        # It will propergate KeyboardInterrupt to all processes including parent process.
        # see:
        # - windows - Trying to implement `signal.CTRL_C_EVENT` in Python3.6 - Stack Overflow
        #   https://stackoverflow.com/a/44147750/12721873
        # - How to handle the signal in python on windows machine - Stack Overflow
        #   https://stackoverflow.com/a/35792192/12721873
        if cancel_futures and sys.platform != "win32":
            self.logger.debug("Shutdown ProcessTaskPoolExecutor: Cancel all process tasks")
            self.process_task_manager.lock_and_send_signal(signal_number)
        self.logger.debug("Shutdown ProcessTaskPoolExecutor: Shutdown ProcessPoolExecutor")
        self.call_super_class_shutdown(wait, cancel_futures)
        self.logger.debug("Shutdown ProcessTaskPoolExecutor: Shutdown sync manager")
        self.sync_manager.shutdown()

    def call_super_class_shutdown(self, wait: bool, cancel_futures: bool) -> None:
        """Calls shutdown() of super class."""
        if sys.version_info >= (3, 9):
            super().shutdown(wait, cancel_futures=cancel_futures)
        else:
            super().shutdown(wait)  # pragma: no cover

    def create_process_task(
        self, function_coroutine: Callable[..., Awaitable[TypeVarReturnValue]], *args: Any
    ) -> Future[TypeVarReturnValue]:
        """Creates task like future by wraping coroutine."""
        return self.process_task_manager.create_process_task(function_coroutine, *args)
