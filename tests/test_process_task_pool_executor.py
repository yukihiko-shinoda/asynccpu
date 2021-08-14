"""Tests for `asynccpu` package."""
import asyncio

# Reason: To support Python 3.8 or less pylint: disable=unused-import
import queue
import sys
import time
from asyncio.futures import Future
from concurrent.futures.process import ProcessPoolExecutor

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from logging import LogRecord
from multiprocessing.context import Process
from multiprocessing.managers import SyncManager
from signal import SIGINT, SIGTERM
from subprocess import Popen
from typing import Any, Callable, List, cast

import psutil
import pytest

# Reason: Following export method in __init__.py from Effective Python 2nd Edition item 85
from asynccpu import ProcessTaskPoolExecutor  # type: ignore
from asynccpu.process_task_pool_executor import ProcessTaskFactory, ProcessTaskManager
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_KEYBOARD_INTERRUPT_CTRL_C_POPEN_SHORT, SECOND_SLEEP_FOR_TEST_SHORT
from tests.testlibraries.assert_log import assert_log
from tests.testlibraries.cpu_bound import expect_process_cpu_bound, process_cpu_bound
from tests.testlibraries.example_use_case import example_use_case, example_use_case_cancel_repost_process_id
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket

if sys.platform == "win32":
    # Reason pylint issue. When put into group, wrong-import-position occur. pylint: disable=ungrouped-imports
    from subprocess import CREATE_NEW_PROCESS_GROUP


class TestProcessTaskManager:
    """Test for ProcessTaskManager."""

    @pytest.mark.asyncio
    async def test(self) -> None:
        """Method: cancel_if_not_cancelled() should cancel task."""
        with SyncManager() as sync_manager:
            with ProcessPoolExecutor() as executor:
                task = await self.execute_test(ProcessTaskFactory(executor, cast(SyncManager, sync_manager)))
        assert task.done()

    @staticmethod
    async def execute_test(process_task_factory: ProcessTaskFactory) -> "Future[Any]":
        """Executes test."""
        process_task_manager = ProcessTaskManager(process_task_factory)
        task = process_task_manager.create_process_task(process_cpu_bound)
        assert not task.done()
        assert not task.cancelled()
        with pytest.raises(Terminated):
            process_task_manager.send_signal(SIGTERM)
            await task
        return task


class TestProcessTaskPoolExecutor:
    """Test for process_task_pool_executor."""

    @staticmethod
    def test_shutdown() -> None:
        with ProcessTaskPoolExecutor() as executor:
            executor.shutdown()

    @staticmethod
    def test_smoke(manager_queue: "queue.Queue[LogRecord]") -> None:
        """
        - Results should be as same as expected.
        - Logging configuration should be as same as default.
        """
        expects = [expect_process_cpu_bound(i) for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
        # The setting [tool.pytest.ini_options] in pyproject.toml
        # doesn't propergate to subprocess on Windows.
        # Default log level in Python is WARN.
        # see:
        #   - Logging HOWTO — Python 3.9.2 documentation
        #     https://docs.python.org/3/howto/logging.html#when-to-use-logging
        expect_info = sys.platform != "win32"
        expect_debug = sys.platform != "win32"
        actuals = asyncio.run(example_use_case(manager_queue))
        assert actuals is not None
        for expect in expects:
            assert expect in actuals
        assert_log(manager_queue, expect_info, expect_debug)

    @staticmethod
    def test_smoke_configure_log(
        manager_queue: "queue.Queue[LogRecord]", configurer_log_level: Callable[[], None]
    ) -> None:
        """ProcessTaskPoolExecutor should be able to configure logging settings."""
        expects = [expect_process_cpu_bound(i) for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
        actuals = asyncio.run(example_use_case(manager_queue, configurer_log_level))
        assert actuals is not None
        for expect in expects:
            assert expect in actuals
        assert_log(manager_queue, True, False)

    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #     https://bugs.python.org/issue26350
    @staticmethod
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    @pytest.mark.asyncio
    async def test_future() -> None:
        """
        Can't test in case process.kill() since it sends signal.SIGKILL and Python can't trap it.
        Function process.kill() stops pytest process.
        see:
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.terminate
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.kill
          - https://docs.python.org/ja/3/library/signal.html#signal.SIGKILL
        """
        with ProcessTaskPoolExecutor(cancel_tasks_when_shutdown=True) as executor:
            future = executor.create_process_task(process_cpu_bound, 1, True)
            pid = LocalSocket.receive()
            process = psutil.Process(int(pid))
            process.terminate()
            with pytest.raises(Terminated):
                await future
            assert future.done()
            assert isinstance(future.exception(), Terminated)

    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #     https://bugs.python.org/issue26350
    @staticmethod
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_terminate(manager_queue: "queue.Queue[LogRecord]") -> None:
        """
        Can't test in case process.kill() since it sends signal.SIGKILL and Python can't trap it.
        Function process.kill() stops pytest process.
        see:
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.terminate
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.kill
          - https://docs.python.org/ja/3/library/signal.html#signal.SIGKILL
        """
        process = Process(target=example_use_case_cancel_repost_process_id, kwargs={"queue_main": manager_queue})
        process.start()
        LocalSocket.receive()
        time.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        psutil_process = psutil.Process(process.pid)
        psutil_process.terminate()
        psutil_process.wait()
        # Reason: Requires to enhance types-psutil
        assert not psutil_process.is_running()  # type: ignore
        assert_graceful_shutdown(manager_queue)

    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #     https://bugs.python.org/issue26350
    @staticmethod
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_sigterm(manager_queue: "queue.Queue[LogRecord]") -> None:
        """ProcessTaskPoolExecutor should raise keyboard interrupt."""
        process = Process(target=example_use_case_cancel_repost_process_id, kwargs={"queue_main": manager_queue})
        process.start()
        LocalSocket.receive()
        time.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        psutil_process = psutil.Process(process.pid)
        psutil_process.send_signal(SIGTERM)
        psutil_process.wait()
        # Reason: Requires to enhance types-psutil
        assert not psutil_process.is_running()  # type: ignore
        assert_graceful_shutdown(manager_queue)

    # Since only SIGTERM, CTRL_C_EVENT and CTRL_BREAK_EVENT signals are supported on Windows.
    # see: https://github.com/giampaolo/psutil/blob/e80cabe5206fd7ef14fd6a47e2571f660f95babf/psutil/_pswindows.py#L875
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_keyboard_interrupt_on_linux(self) -> None:
        """
        - Keyboard interrupt should reach to all descendant processes.
        - Keyboard interrupt should shutdown ProcessTaskPoolExecutor gracefully.
        """
        process = Process(target=self.report_raises_keyboard_interrupt)
        process.start()
        LocalSocket.receive()
        time.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        self.simulate_ctrl_c_in_posix(process)
        assert LocalSocket.receive() == "Test succeed"
        process.join()
        assert process.exitcode == 0
        assert not process.is_alive()

    @staticmethod
    @pytest.mark.skipif(sys.platform != "win32", reason="test for Windows only")
    def test_keyboard_interrupt_ctrl_c_new_window() -> None:
        """
        see:
          - Answer: Sending ^C to Python subprocess objects on Windows
            https://stackoverflow.com/a/7980368/12721873
        """
        with Popen(f"start {sys.executable} tests\\testlibraries\\subprocess_wrapper_windows.py", shell=True) as popen:
            assert LocalSocket.receive() == "Test succeed"
            assert popen.wait() == 0

    @staticmethod
    @pytest.mark.skipif(sys.platform != "win32", reason="test for Windows only")
    def test_keyboard_interrupt_ctrl_c_popen() -> None:
        """
        see:
          - On Windows, what is the python launcher 'py' doing that lets control-C cross between process groups?
            https://stackoverflow.com/q/42180468/12721873
            https://github.com/njsmith/appveyor-ctrl-c-test/blob/34e13fab9be56d59c3eba566e26d80505c309438/a.py
            https://github.com/njsmith/appveyor-ctrl-c-test/blob/34e13fab9be56d59c3eba566e26d80505c309438/run-a.py
        """
        with Popen(
            f"{sys.executable} tests\\testlibraries\\keyboaard_interrupt_in_windows.py",
            # Reason: Definition of following constant is Windows only
            creationflags=CREATE_NEW_PROCESS_GROUP,  # type: ignore
        ) as popen:
            asyncio.run(asyncio.sleep(SECOND_SLEEP_FOR_TEST_KEYBOARD_INTERRUPT_CTRL_C_POPEN_SHORT))
            LocalSocket.send(str(popen.pid))
            assert LocalSocket.receive() == "Test succeed"
            assert popen.wait() == 0

    @staticmethod
    def report_raises_keyboard_interrupt() -> None:
        with pytest.raises(KeyboardInterrupt):
            example_use_case_cancel_repost_process_id()
        LocalSocket.send("Test succeed")

    @staticmethod
    def simulate_ctrl_c_in_posix(process: Process) -> None:
        """
        see:
          - python - Handling keyboard interrupt when using subproccess - Stack Overflow
            https://stackoverflow.com/a/23839524/12721873
          - Answer: c++ - Child process receives parent's SIGINT - Stack Overflow
            https://stackoverflow.com/a/6804155/12721873
        """
        psutil_process = psutil.Process(process.pid)
        child_processes: List[psutil.Process] = psutil_process.children(recursive=True)
        child_processes.append(psutil_process)
        for child_process in child_processes:
            child_process.send_signal(SIGINT)


def assert_graceful_shutdown(queue_logger: "queue.Queue[LogRecord]") -> None:
    """Asserts graceful shutdown."""
    log_checker = LogChecker()
    while not queue_logger.empty():
        log_checker.check(queue_logger.get().message)
    assert log_checker.finish_lock_and_cancel_if_not_cancelled
    assert log_checker.finish_sigterm_hander


class LogChecker:
    """Checks log records."""

    def __init__(self) -> None:
        self.finish_lock_and_cancel_if_not_cancelled = False
        self.finish_sigterm_hander = False

    def check(self, message: str) -> None:
        if message == "Lock and send signal: Finish":
            self.finish_lock_and_cancel_if_not_cancelled = True
        elif message == "SIGTERM handler ProcessTaskPoolExecutor: Finish":
            self.finish_sigterm_hander = True
