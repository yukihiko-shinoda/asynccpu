"""Test for process_cpu_bound.py."""

import multiprocessing
import sys
from concurrent.futures.process import ProcessPoolExecutor
from logging import getLogger
from multiprocessing import Process

import psutil
import pytest

from tests.testlibraries.cpu_bound import cpu_bound
from tests.testlibraries.cpu_bound import process_cpu_bound_method
from tests.testlibraries.exceptions import Terminated
from tests.testlibraries.local_socket import LocalSocket


class TestProcessCpuBound:
    """Test for ProcessCpuBound."""

    @staticmethod
    def test_method() -> None:
        """CPU bound should be terminated when method."""
        parent_conn, child_conn = multiprocessing.Pipe()
        process = Process(
            target=process_cpu_bound_method,
            args=(1,),
            kwargs={"send_process_id": True, "connection": child_conn},
        )
        process.start()
        pid = LocalSocket.receive()
        getLogger(__name__).debug("Terminate process id: %s", pid)
        psutil_process = psutil.Process(int(pid))
        psutil_process.terminate()
        process.join()
        assert not parent_conn.poll()

    @staticmethod
    # Since Python can't trap signal.SIGTERM in Windows.
    # see:
    #     - Windows: signal doc should state certains signals can't be registered
    #     https://bugs.python.org/issue26350
    @pytest.mark.skipif(sys.platform == "win32", reason="test for Linux only")
    def test_coroutine() -> None:
        """CPU bound should be terminated when coroutine."""
        with ProcessPoolExecutor() as executor:
            future = executor.submit(cpu_bound, 1, send_process_id=True)
            pid = LocalSocket.receive()
            getLogger(__name__).debug("Terminate process id: %s", pid)
            psutil_process = psutil.Process(int(pid))
            psutil_process.terminate()
            assert isinstance(future.exception(), Terminated)
            assert future.done()
