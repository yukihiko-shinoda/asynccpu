"""The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
import asyncio

from asynccpu import ProcessTaskPoolExecutor
from tests.testlibraries.cpu_bound import process_cpu_bound


async def example_use_case_cancel() -> None:
    """The example use case of ProcessTaskPoolExecutor for E2E testing in case of cancel."""
    with ProcessTaskPoolExecutor(max_workers=3, cancel_tasks_when_shutdown=True) as executor:
        futures = {executor.create_process_task(process_cpu_bound, x) for x in range(10)}
        await asyncio.gather(*futures)
        raise Exception("Failed")
