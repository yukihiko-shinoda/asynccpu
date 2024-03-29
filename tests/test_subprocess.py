"""Test for subprocess.py."""
import _thread
import asyncio
import os

# Reason: To support Python 3.8 or less pylint: disable=unused-import
import queue
import sys
from asyncio.futures import Future
from concurrent.futures.process import ProcessPoolExecutor

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from logging import LogRecord, getLogger
from multiprocessing.managers import SyncManager
from typing import Any, Callable, Dict, List, cast

import psutil
import pytest
from pytest_mock import MockerFixture

from asynccpu.process_task import ProcessTask
from asynccpu.subprocess import LoggingInitializer, Replier, cancel_coroutine, run
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_MIDDLE
from tests.testlibraries.assert_log import assert_log
from tests.testlibraries.cpu_bound import expect_process_cpu_bound, process_cpu_bound
from tests.testlibraries.process_family import ProcessFamily


async def keyboard_interrupt() -> None:
    await process_cpu_bound()
    _thread.interrupt_main()


class TestRun:
    """Test for run()."""

    @staticmethod
    def test_run(manager_queue: "queue.Queue[LogRecord]", replier: Replier) -> None:
        """Function: run should run coroutine function from beggining to end."""
        expect = expect_process_cpu_bound(1)
        logging_initializer = LoggingInitializer(manager_queue)
        actual = run(replier, logging_initializer, process_cpu_bound, 1)
        assert actual == expect
        assert_log(manager_queue, True, True)

    @staticmethod
    def test_run_configure_log(
        manager_queue: "queue.Queue[LogRecord]", configurer_log_level: Callable[[], None], replier: Replier
    ) -> None:
        """Function: run should be able to configure log settings."""
        expect = expect_process_cpu_bound(1)
        logging_initializer = LoggingInitializer(manager_queue, configurer_log_level)
        actual = run(replier, logging_initializer, process_cpu_bound, 1)
        assert actual == expect
        assert_log(manager_queue, True, False)

    @staticmethod
    def test_run_keyboard_interrupt(sync_manager: SyncManager) -> None:
        """Function: run should stop by keyboard interupt."""
        queue_process_id = sync_manager.Queue()
        replier = Replier(sync_manager.dict(), queue_process_id)
        loop = asyncio.new_event_loop()
        with ProcessPoolExecutor() as executor:
            future = cast("Future[Any]", loop.run_in_executor(executor, run, replier, None, keyboard_interrupt))
            queue_process_id.get()
        assert not future.get_loop().is_running()
        assert not future.done()

    def test_run_terminate(self) -> None:
        """Function run() should stop when send signal for terminate to child processes."""
        self.execute_test_run(self.terminate)

    def test_run_kill(self) -> None:
        """Function run() should stop when send signal for kill to child processes."""
        self.execute_test_run(self.kill)

    @classmethod
    def execute_test_run(cls, send_signal: Callable[[psutil.Process], None]) -> None:
        """Executes test run"""
        expect = expect_process_cpu_bound(1)
        future = cls.run_in_process_executor(1)
        cls.execute_send_signal(send_signal)
        loop = future.get_loop()
        assert not loop.is_running()
        loop.run_until_complete(asyncio.wait_for(future, SECOND_SLEEP_FOR_TEST_MIDDLE))
        assert future.done()
        assert future.result() == expect
        assert future.exception() is None

    @staticmethod
    def execute_send_signal(send_signal: Callable[[psutil.Process], None]) -> None:
        pytest_process = psutil.Process()
        children: List[psutil.Process] = pytest_process.children()
        for process in children:
            send_signal(process)

    @staticmethod
    def run_in_process_executor(task_id: Any) -> "Future[Any]":
        """Sends signal for test."""
        loop = asyncio.new_event_loop()
        with ProcessPoolExecutor() as executor:
            with SyncManager() as manager:
                sync_mangaer = cast(SyncManager, manager)
                dictionary_process: Dict[int, ProcessTask] = sync_mangaer.dict()
                queue_process_id: "queue.Queue[ProcessTask]" = sync_mangaer.Queue()
                replier = Replier(dictionary_process, queue_process_id)
                future = cast(
                    "Future[Any]", loop.run_in_executor(executor, run, replier, None, process_cpu_bound, task_id),
                )
                process: ProcessTask = queue_process_id.get()
                assert process.id in dictionary_process
                return future

    @staticmethod
    def terminate(process: psutil.Process) -> None:
        process.terminate()

    @staticmethod
    def kill(process: psutil.Process) -> None:
        process.kill()


class TestCancelCoroutine:
    """Test for cancel_coroutine()."""

    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_unified(self) -> None:
        """
        Function terminate_process() should terminate all child processes.

        Can't test in case process.kill() since it sends signal.SIGKILL and Python can't trap it.
        Function process.kill() stops pytest process.
        see:
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.terminate
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.kill
          - https://docs.python.org/ja/3/library/signal.html#signal.SIGKILL
        """
        process_family = ProcessFamily(self.execute_cancel_coroutine)
        process_family.assert_that_descendant_processes_are_terminated()

    @classmethod
    def execute_cancel_coroutine(cls) -> None:
        cancel_coroutine(getLogger())

    @staticmethod
    def test_unit(mocker: MockerFixture) -> None:
        mock_terminate_processes = mocker.MagicMock()
        mocker.patch("asynccpu.subprocess.terminate_descendant_processes", mock_terminate_processes)
        cancel_coroutine(getLogger())
        mock_terminate_processes.assert_called_once_with(os.getpid())
