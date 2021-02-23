"""Tests for `asynccpu` package."""
import _thread
import asyncio
import multiprocessing
import os
import signal
import sys
import threading
from asyncio.exceptions import CancelledError
from asyncio.futures import Future
from concurrent.futures.process import ProcessPoolExecutor
from logging import getLogger
from multiprocessing.context import Process
from subprocess import Popen
from typing import Any, Callable, List, cast

import psutil
import pytest

from asynccpu import ProcessTaskPoolExecutor
from asynccpu.process_task_pool_executor import run, terminate_processes
from tests.testlibraries import (
    SECOND_SLEEP_FOR_TEST_KEYBOARD_INTERRUPT_CTRL_C_POPEN_SHORT,
    SECOND_SLEEP_FOR_TEST_MIDDLE,
    SECOND_SLEEP_FOR_TEST_SHORT,
)
from tests.testlibraries.cpu_bound import expect_process_cpu_bound, process_cpu_bound
from tests.testlibraries.local_socket import LocalSocket

if sys.platform == "win32":
    # Reason pylint issue. When put into group, wrong-import-position occur. pylint: disable=ungrouped-imports
    from subprocess import CREATE_NEW_PROCESS_GROUP


async def keyboard_interrupt() -> None:
    await process_cpu_bound()
    _thread.interrupt_main()


class TestRun:
    """Test for run()."""

    @staticmethod
    def test_run() -> None:
        expect = expect_process_cpu_bound(1)
        actual = run(process_cpu_bound, 1)
        assert actual == expect

    @staticmethod
    def test_run_keyboard_interrupt() -> None:
        loop = asyncio.new_event_loop()
        with ProcessPoolExecutor() as executor:
            future = cast(Future, loop.run_in_executor(executor, run, keyboard_interrupt))
        assert not future.get_loop().is_running()
        assert not future.done()

    def test_run_terminate(self) -> None:
        """Function run() should stop when send signal for terminate to child processes."""
        self.execute_test_run(self.terminate)

    def test_run_kill(self) -> None:
        """Function run() should stop when send signal for kill to child processes."""
        self.execute_test_run(self.kill)

    @classmethod
    def execute_test_run(cls, send_signal: Callable[[Process], None]):
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
    def execute_send_signal(send_signal: Callable[[Process], None]):
        pytest_process = psutil.Process(os.getpid())
        children = pytest_process.children()
        for process in children:
            send_signal(process)

    @staticmethod
    def run_in_process_executor(task_id: Any) -> Future:
        """Sends signal for test."""
        loop = asyncio.new_event_loop()
        with ProcessPoolExecutor() as executor:
            return cast(Future, loop.run_in_executor(executor, run, process_cpu_bound, task_id))

    @staticmethod
    def terminate(process: Process) -> None:
        process.terminate()

    @staticmethod
    def kill(process: Process) -> None:
        process.kill()


class TestTerminateProcess:
    """Test for terminate_process()."""

    def test_terminate_processes(self) -> None:
        """Function terminate_process() should terminate all child processes."""

        def execute_terminate_processes(process_id: int):
            terminate_processes(process_id)

        self.execute_test_terminate_processes(execute_terminate_processes)

    def test_terminate_processes_force(self) -> None:
        """Function terminate_process() should kill all child processes."""

        def execute_terminate_processes(process_id: int):
            terminate_processes(process_id, force=True)

        self.execute_test_terminate_processes(execute_terminate_processes)

    @classmethod
    def execute_test_terminate_processes(cls, callable_execute_terminate_processes: Callable[[int], None]):
        """Executes test for terminate_process()."""
        child_process = cls.create_child_process()
        grandchildren = cls.get_grandchildren_process(child_process)
        assert child_process.pid is not None
        callable_execute_terminate_processes(child_process.pid)
        multiprocessing.connection.wait([child_process.sentinel])
        cls.assert_that_descendant_processes_are_terminated(child_process, grandchildren)

    @classmethod
    def create_child_process(cls) -> Process:
        """Creates child process for test."""
        event = multiprocessing.Event()
        child_process = Process(target=cls.child, args=(event,))
        child_process.start()
        assert child_process.is_alive()
        event.wait()
        return child_process

    @staticmethod
    def get_grandchildren_process(child_process: Process) -> List[psutil.Process]:
        """Creates grandchildren processes for test."""
        psutil_child_process = psutil.Process(child_process.pid)
        grandchildren = psutil_child_process.children(recursive=True)
        assert grandchildren
        for grandchild in grandchildren:
            assert grandchild.is_running()
        return grandchildren

    @classmethod
    def child(cls, event: threading.Event) -> None:
        Process(target=cls.process_cpu_bound).start()
        event.set()

    @staticmethod
    def process_cpu_bound() -> None:
        asyncio.run(process_cpu_bound())

    @staticmethod
    def assert_that_descendant_processes_are_terminated(child_process: Process, grandchildren: List[psutil.Process]):
        _, alive = psutil.wait_procs(grandchildren, timeout=1)
        assert not alive
        assert not child_process.is_alive()
        for grandchild in grandchildren:
            assert not grandchild.is_running()


class TestProcessTaskPoolExecutor:
    """Test for process_task_pool_executor."""

    LOGGER = getLogger(__name__)

    def test_smoke(self) -> None:
        expects = [expect_process_cpu_bound(i) for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
        actuals = asyncio.run(self.example_use_case())
        assert actuals is not None
        for expect in expects:
            assert expect in actuals

    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #     https://bugs.python.org/issue26350
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_keyboard_interrupt(self) -> None:

        signal.signal(signal.SIGTERM, self.disable_termination)
        asyncio.run(self.keyboard_interrupt_terminate())

    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #     https://bugs.python.org/issue26350
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_keyboard_interrupt_sigterm(self) -> None:
        signal.signal(signal.SIGTERM, self.disable_termination)
        asyncio.run(self.keyboard_interrupt_sigterm())

    @staticmethod
    def disable_termination(_signum, _frame):
        pass

    # Since only SIGTERM, CTRL_C_EVENT and CTRL_BREAK_EVENT signals are supported on Windows.
    # see: https://github.com/giampaolo/psutil/blob/e80cabe5206fd7ef14fd6a47e2571f660f95babf/psutil/_pswindows.py#L875
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_keyboard_interrupt_on_linux(self) -> None:
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(self.keyboard_interrupt(signal.SIGINT))

    @staticmethod
    @pytest.mark.skipif(sys.platform != "win32", reason="test for Windows only")
    def test_keyboard_interrupt_ctrl_c_new_window() -> None:
        """
        see:
          - Answer: Sending ^C to Python subprocess objects on Windows
            https://stackoverflow.com/a/7980368/12721873
        """
        popen = Popen(f"start {sys.executable} tests\\testlibraries\\subprocess_wrapper_windows.py", shell=True)
        assert LocalSocket.receive() == "Test succeed"
        assert popen.wait() == 0

    @staticmethod
    @pytest.mark.skipif(sys.platform != "win32", reason="test for Windows only")
    def test_keyboard_interrupt_ctrl_c_popen():
        """
        see:
          - On Windows, what is the python launcher 'py' doing that lets control-C cross between process groups?
            https://stackoverflow.com/q/42180468/12721873
            https://github.com/njsmith/appveyor-ctrl-c-test/blob/34e13fab9be56d59c3eba566e26d80505c309438/a.py
            https://github.com/njsmith/appveyor-ctrl-c-test/blob/34e13fab9be56d59c3eba566e26d80505c309438/run-a.py
        """
        popen = Popen(
            f"{sys.executable} tests\\testlibraries\\keyboaard_interrupt_in_windows.py",
            creationflags=CREATE_NEW_PROCESS_GROUP,
        )
        asyncio.run(asyncio.sleep(SECOND_SLEEP_FOR_TEST_KEYBOARD_INTERRUPT_CTRL_C_POPEN_SHORT))
        LocalSocket.send(str(popen.pid))
        assert LocalSocket.receive() == "Test succeed"
        assert popen.wait() == 0

    @classmethod
    async def keyboard_interrupt_terminate(cls) -> None:
        """
        Can't test in case process.kill() since it sends signal.SIGKILL and Python can't trap it.
        Function process.kill() stops pytest process.
        see:
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.terminate
          - https://psutil.readthedocs.io/en/latest/#psutil.Process.kill
          - https://docs.python.org/ja/3/library/signal.html#signal.SIGKILL
        """
        task = asyncio.create_task(cls.example_use_case_cancel())
        await asyncio.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        current_process = psutil.Process(os.getpid())
        try:
            current_process.terminate()
        except CancelledError:
            await task
            assert task.done()
            assert isinstance(task.exception(), KeyboardInterrupt)

    @classmethod
    async def keyboard_interrupt_sigterm(cls) -> None:
        """Simulates keyboard interrupt by SIGTERM."""
        task = asyncio.create_task(cls.example_use_case_cancel())
        await asyncio.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        current_process = psutil.Process(os.getpid())
        try:
            current_process.send_signal(signal.SIGTERM)
        except CancelledError:
            await task
            assert task.done()
            assert task.exception() is None

    @classmethod
    async def keyboard_interrupt(cls, signal_number: int, pid=None) -> None:
        """Simulates keyboard interrupt."""
        if pid is None:
            pid = os.getpid()
        task = asyncio.create_task(cls.example_use_case_cancel())
        await asyncio.sleep(SECOND_SLEEP_FOR_TEST_SHORT)
        current_process = psutil.Process(pid)
        try:
            current_process.send_signal(signal_number)
            await task
        except CancelledError:
            await task
            assert task.done()
            assert task.exception() is None

    @staticmethod
    async def example_use_case() -> List[Future]:
        """The example use case of ProcessTaskPoolExecutor for E2E testing."""
        with ProcessTaskPoolExecutor(max_workers=3, cancel_tasks_when_shutdown=True) as executor:
            futures = {executor.create_process_task(process_cpu_bound, x) for x in range(10)}
            return await asyncio.gather(*futures)

    @staticmethod
    async def example_use_case_cancel() -> None:
        """The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
        with ProcessTaskPoolExecutor(max_workers=3, cancel_tasks_when_shutdown=True) as executor:
            futures = {executor.create_process_task(process_cpu_bound, x) for x in range(10)}
            await asyncio.gather(*futures)
            pytest.fail()
