"""Configuration of pytest"""
# Reason: To support Python 3.8 or less pylint: disable=unused-import
import queue
from logging import INFO, getLogger, root
from multiprocessing.managers import SyncManager
from typing import Any, Callable, Generator, cast

import pytest

from asynccpu.subprocess import Replier

collect_ignore = ["setup.py"]


@pytest.fixture
def sync_manager() -> Generator[SyncManager, None, None]:
    with SyncManager() as manager:
        yield cast(SyncManager, manager)


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def manager_queue(sync_manager: SyncManager) -> Generator["queue.Queue[Any]", None, None]:
    yield sync_manager.Queue()


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def replier(sync_manager: SyncManager) -> Generator[Replier, None, None]:
    yield Replier(sync_manager.dict(), sync_manager.Queue())


def configure_log_level() -> None:
    root_logger = getLogger()
    root_logger.setLevel(INFO)


@pytest.fixture
def configurer_log_level() -> Generator[Callable[[], None], None, None]:
    temporary_level = root.level
    yield configure_log_level
    root_logger = getLogger()
    root_logger.setLevel(temporary_level)
