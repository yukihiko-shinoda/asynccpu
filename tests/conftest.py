"""Configuration of pytest"""
import queue
from logging import INFO, getLogger, root
from multiprocessing.managers import SyncManager
from typing import Any, Callable, Dict, Generator, cast

import pytest

collect_ignore = ["setup.py"]


@pytest.fixture
def sync_manager() -> Generator[SyncManager, None, None]:
    with SyncManager() as manager:
        yield cast(SyncManager, manager)


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def manager_queue(sync_manager: SyncManager) -> Generator[queue.Queue[Any], None, None]:
    yield sync_manager.Queue()


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def manager_queue_2(sync_manager: SyncManager) -> Generator[queue.Queue[Any], None, None]:
    yield sync_manager.Queue()


@pytest.fixture
# Reason: To refer other fixture. pylint: disable=redefined-outer-name
def manager_dict(sync_manager: SyncManager) -> Generator[Dict[Any, Any], None, None]:
    yield sync_manager.dict()


def configure_log_level() -> None:
    root_logger = getLogger()
    root_logger.setLevel(INFO)


@pytest.fixture
def configurer_log_level() -> Generator[Callable[[], None], None, None]:
    temporary_level = root.level
    yield configure_log_level
    root_logger = getLogger()
    root_logger.setLevel(temporary_level)
