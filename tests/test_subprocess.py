"""Test for subprocess.py."""
from asynccpu.subprocess import ProcessForWeakSet


class TestProcessForWeakSet:
    """Test for ProcessForWeakSet."""

    @staticmethod
    def test() -> None:
        process1 = ProcessForWeakSet(1)
        process2 = ProcessForWeakSet(1)
        list_process = [process1]
        assert list_process[0] == process1
        assert list_process[0] != process2
