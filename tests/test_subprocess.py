"""Test for subprocess.py."""
import _thread
import asyncio
import multiprocessing
import queue
from asyncio.futures import Future
from concurrent.futures.process import ProcessPoolExecutor
from logging import LogRecord, getLogger
from multiprocessing import synchronize
from multiprocessing.context import Process
from multiprocessing.managers import SyncManager
from typing import Any, Callable, Dict, List, cast

import psutil

from asynccpu.subprocess import ProcessForWeakSet, cancel_coroutine, run, terminate_processes
from tests.testlibraries import SECOND_SLEEP_FOR_TEST_MIDDLE
from tests.testlibraries.assert_log import assert_log
from tests.testlibraries.cpu_bound import cpu_bound, expect_process_cpu_bound, process_cpu_bound


async def keyboard_interrupt() -> None:
    await process_cpu_bound()
    _thread.interrupt_main()


class TestProcessForWeakSet:
    """Test for ProcessForWeakSet."""

    @staticmethod
    def test() -> None:
        process1 = ProcessForWeakSet(1)
        process2 = ProcessForWeakSet(1)
        list_process = [process1]
        assert list_process[0] == process1
        assert list_process[0] != process2


class TestRun:
    """Test for run()."""

    @staticmethod
    def test_run(
        manager_dict: Dict[int, ProcessForWeakSet],
        manager_queue: queue.Queue[ProcessForWeakSet],
        manager_queue_2: queue.Queue[LogRecord],
    ) -> None:
        """Function: run should run coroutine function from beggining to end."""
        expect = expect_process_cpu_bound(1)
        actual = run(manager_dict, manager_queue, manager_queue_2, None, process_cpu_bound, 1)
        assert actual == expect
        assert_log(manager_queue_2, True, True)

    @staticmethod
    def test_run_configure_log(
        manager_dict: Dict[int, ProcessForWeakSet],
        manager_queue: queue.Queue[ProcessForWeakSet],
        manager_queue_2: queue.Queue[LogRecord],
        configurer_log_level: Callable[[], None],
    ) -> None:
        """Function: run should be able to configure log settings."""
        expect = expect_process_cpu_bound(1)
        actual = run(manager_dict, manager_queue, manager_queue_2, configurer_log_level, process_cpu_bound, 1)
        assert actual == expect
        assert_log(manager_queue_2, True, False)

    @staticmethod
    def test_run_keyboard_interrupt(
        manager_dict: Dict[int, ProcessForWeakSet], manager_queue: queue.Queue[ProcessForWeakSet]
    ) -> None:
        """Function: run should stop by keyboard interupt."""
        loop = asyncio.new_event_loop()
        with ProcessPoolExecutor() as executor:
            future = cast(
                Future[Any],
                loop.run_in_executor(executor, run, manager_dict, manager_queue, None, None, keyboard_interrupt),
            )
            manager_queue.get()
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
    def run_in_process_executor(task_id: Any) -> Future[Any]:
        """Sends signal for test."""
        loop = asyncio.new_event_loop()
        with ProcessPoolExecutor() as executor:
            with SyncManager() as manager:
                sync_mangaer = cast(SyncManager, manager)
                dictionary_process: Dict[int, ProcessForWeakSet] = sync_mangaer.dict()
                queue_process_id: queue.Queue[ProcessForWeakSet] = sync_mangaer.Queue()
                future = cast(
                    Future[Any],
                    loop.run_in_executor(
                        executor, run, dictionary_process, queue_process_id, None, None, process_cpu_bound, task_id
                    ),
                )
                process: ProcessForWeakSet = queue_process_id.get()
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

    def test_cancel_coroutine(self) -> None:
        """Function terminate_process() should terminate all child processes."""
        process_family = ProcessFamily(self.child)
        multiprocessing.connection.wait([process_family.child_process.sentinel])
        process_family.assert_that_descendant_processes_are_terminated()

    @classmethod
    def child(cls, event: synchronize.Event) -> None:
        Process(target=cpu_bound).start()
        event.set()
        cancel_coroutine(getLogger())


class TestTerminateProcess:
    """Test for terminate_process()."""

    def test_terminate_processes(self) -> None:
        """Function terminate_process() should terminate all child processes."""

        def execute_terminate_processes(process_id: int) -> None:
            terminate_processes(process_id)

        self.execute_test_terminate_processes(execute_terminate_processes)

    def test_terminate_processes_force(self) -> None:
        """Function terminate_process() should kill all child processes."""

        def execute_terminate_processes(process_id: int) -> None:
            terminate_processes(process_id, force=True)

        self.execute_test_terminate_processes(execute_terminate_processes)

    @classmethod
    def execute_test_terminate_processes(cls, callable_execute_terminate_processes: Callable[[int], None]) -> None:
        """Executes test for terminate_process()."""
        process_family = ProcessFamily(cls.child)
        pid = process_family.child_process.pid
        assert pid is not None
        callable_execute_terminate_processes(pid)
        multiprocessing.connection.wait([process_family.child_process.sentinel])
        process_family.assert_that_descendant_processes_are_terminated()

    @classmethod
    def child(cls, event: synchronize.Event) -> None:
        Process(target=cpu_bound).start()
        event.set()


class ProcessFamily:
    """Creates child process and grandchild process ad once."""

    def __init__(self, child: Callable[[synchronize.Event], Any]) -> None:
        self.child_process = self.create_child_process(child)
        self.grandchildren = self.get_grandchildren_process(self.child_process)
        assert self.child_process.pid is not None

    @classmethod
    def create_child_process(cls, child: Callable[[synchronize.Event], Any]) -> Process:
        """Creates child process for test."""
        event = multiprocessing.Event()
        child_process = Process(target=child, args=(event,))
        child_process.start()
        assert child_process.is_alive()
        event.wait()  # for starting grandchild process
        return child_process

    @staticmethod
    def get_grandchildren_process(child_process: Process) -> List[psutil.Process]:
        """Creates grandchildren processes for test."""
        psutil_child_process = psutil.Process(child_process.pid)
        grandchildren: List[psutil.Process] = psutil_child_process.children(recursive=True)
        assert grandchildren
        for grandchild in grandchildren:
            # Reason: Requires to enhance types-psutil
            assert grandchild.is_running()  # type: ignore
        return grandchildren

    def assert_that_descendant_processes_are_terminated(self) -> None:
        _, alive = psutil.wait_procs(self.grandchildren, timeout=1)
        assert not alive
        assert not self.child_process.is_alive()
        for grandchild in self.grandchildren:
            # Reason: Requires to enhance types-psutil
            assert not grandchild.is_running()  # type: ignore
