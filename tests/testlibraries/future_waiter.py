"""Waits without async/await syntax."""

from __future__ import annotations

__author__ = "Yukihiko Shinoda"
__copyright__ = "Copyright (c) 2021 Yukihiko Shinoda"
__license__ = "MIT"

import asyncio
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

if TYPE_CHECKING:
    from asyncio.futures import Future


class FutureWaiter:
    """Waits without async/await syntax."""

    @classmethod
    def wait(cls, futures: Iterable[Future[Any]]) -> None:
        asyncio.get_event_loop().run_until_complete(asyncio.wait(futures))

    @staticmethod
    def wait_for(future: Future[Any], timeout: int | None = None) -> None:
        future.get_loop().run_until_complete(asyncio.wait_for(future, timeout))
