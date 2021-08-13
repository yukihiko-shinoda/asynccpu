"""Test for process_terminator.py."""
from typing import Callable

from asynccpu.subprocess import terminate_processes
from tests.testlibraries.process_family import ProcessFamily


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
        process_family = ProcessFamily()
        callable_execute_terminate_processes(process_family.child_process.pid)
        process_family.assert_that_descendant_processes_are_terminated()
