"""Test stub of terminate_process()."""

from __future__ import annotations

import multiprocessing
from multiprocessing import Process
from multiprocessing import synchronize
from typing import Any
from typing import Callable

import psutil

from tests.testlibraries.cpu_bound import cpu_bound


class ProcessFamily:
    """Creates child process and grandchild process ad once."""

    def __init__(self, after_task: Callable[[], Any] | None = None) -> None:
        self.child_process = self.create_child_process(after_task)
        self.grandchildren = self.get_grandchildren_process(self.child_process)
        assert self.child_process.pid is not None

    @classmethod
    def create_child_process(cls, after_task: Callable[[], Any] | None = None) -> Process:
        """Creates child process for test."""
        event = multiprocessing.Event()
        child_process = Process(target=cls.child, args=(event, after_task))
        child_process.start()
        assert child_process.is_alive()
        event.wait()  # for starting grandchild process
        return child_process

    @staticmethod
    def get_grandchildren_process(child_process: Process) -> list[psutil.Process]:
        """Creates grandchildren processes for test."""
        psutil_child_process = psutil.Process(child_process.pid)
        grandchildren: list[psutil.Process] = psutil_child_process.children(recursive=True)
        assert grandchildren
        for grandchild in grandchildren:
            assert grandchild.is_running()
        return grandchildren

    def assert_that_descendant_processes_are_terminated(self) -> None:
        """Checks that decendant processes are terminated."""
        self.child_process.join()
        _, alive = psutil.wait_procs(self.grandchildren, timeout=1)
        assert not alive
        assert not self.child_process.is_alive()
        assert self.child_process.exitcode == 0
        self._assert_that_descendant_processes_are_terminated()

    def _assert_that_descendant_processes_are_terminated(self) -> None:
        for grandchild in self.grandchildren:
            assert not grandchild.is_running()

    @staticmethod
    def child(event: synchronize.Event, after_task: Callable[..., Any] | None = None) -> None:
        Process(target=cpu_bound).start()
        event.set()
        if after_task:
            after_task()
