"""Test for process_terminator.py."""

from typing import Callable

from asynccpu.process_terminator import terminate_descendant_processes
from tests.testlibraries.process_family import ProcessFamily


class TestTerminateProcess:
    """Test for terminate_process()."""

    def test_terminate_descendant_processes(self) -> None:
        """Function terminate_process() should terminate all child processes."""

        def callable_sut(process_id: int) -> None:
            terminate_descendant_processes(process_id)

        self.execute_test_terminate_processes(callable_sut)

    def test_terminate_descendant_processes_force(self) -> None:
        """Function terminate_process() should kill all child processes."""

        def callable_sut(process_id: int) -> None:
            terminate_descendant_processes(process_id, force=True)

        self.execute_test_terminate_processes(callable_sut)

    @classmethod
    def execute_test_terminate_processes(cls, callable_terminate_descendant_processes: Callable[[int], None]) -> None:
        """Executes test for terminate_process()."""
        process_family = ProcessFamily()
        assert process_family.child_process.pid
        callable_terminate_descendant_processes(process_family.child_process.pid)
        process_family.assert_that_descendant_processes_are_terminated()
