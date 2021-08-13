"""Waits without async/await syntax."""
import asyncio

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from asyncio.futures import Future

# Reason: To support Python 3.8 or less pylint: disable=unused-import
from typing import Any, Iterable, Optional


class FutureWaiter:
    """Waits without async/await syntax."""

    @classmethod
    def wait(cls, futures: Iterable["Future[Any]"]) -> None:
        asyncio.get_event_loop().run_until_complete(asyncio.wait(futures))

    @staticmethod
    def wait_for(future: "Future[Any]", timeout: Optional[int] = None) -> None:
        future.get_loop().run_until_complete(asyncio.wait_for(future, timeout))
