"""
Cpu bound.
see: https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools
"""


async def process_cpu_bound(task_id: int = None):
    """
    CPU-bound operations will block the event loop:
    in general it is preferable to run them in a process pool.
    """
    return ("" if task_id is None else f"task_id: {task_id}, ") + f"result: {sum(i * i for i in range(10 ** 7))}"


def expect_process_cpu_bound(task_id: int = None):
    return ("" if task_id is None else f"task_id: {task_id}, ") + "result: 333333283333335000000"
