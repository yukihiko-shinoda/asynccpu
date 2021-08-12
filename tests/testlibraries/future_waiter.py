"""Waits without async/await syntax."""
import asyncio
from asyncio.futures import Future
from typing import Any, Iterable, Optional


class FutureWaiter:
    """Waits without async/await syntax."""

    @classmethod
    def wait(cls, futures: Iterable[Future[Any]]) -> None:
        asyncio.get_event_loop().run_until_complete(asyncio.wait(futures))

    @staticmethod
    def wait_for(future: Future[Any], timeout: Optional[int] = None) -> None:
        future.get_loop().run_until_complete(asyncio.wait_for(future, timeout))
