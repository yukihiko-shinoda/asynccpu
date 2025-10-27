"""Configuration of pytest."""

from __future__ import annotations

import asyncio
from logging import INFO
from logging import getLogger
from logging import root
from multiprocessing.managers import SyncManager
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Generator

import pytest

from asynccpu.subprocess import Replier

if TYPE_CHECKING:
    import queue


collect_ignore = ["setup.py"]


pytest.register_assert_rewrite("tests.testlibraries.process_family")


@pytest.fixture
def sync_manager() -> Generator[SyncManager, None, None]:
    with SyncManager() as manager:
        yield manager


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def manager_queue(sync_manager: SyncManager) -> queue.Queue[Any]:
    return sync_manager.Queue()


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def replier(sync_manager: SyncManager) -> Replier:
    return Replier(sync_manager.dict(), sync_manager.Queue())


def configure_log_level() -> None:
    root_logger = getLogger()
    root_logger.setLevel(INFO)


@pytest.fixture
def configurer_log_level() -> Generator[Callable[[], None], None, None]:
    temporary_level = root.level
    yield configure_log_level
    root_logger = getLogger()
    root_logger.setLevel(temporary_level)


@pytest.fixture(autouse=True)
def ensure_event_loop() -> Generator[None, None, None]:
    """Ensure event loop exists for multiprocessing tests.

    This fixture is needed because Python 3.10+ changed the behavior of asyncio.get_event_loop() to raise RuntimeError
    when called from a thread with no running event loop, instead of creating a new one.
    """
    # Check if there's already an event loop set
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            # Loop is closed, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            yield
            loop.close()
        else:
            # Loop exists and is not closed, use it
            yield
    except RuntimeError:
        # No event loop exists, create and set a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()
