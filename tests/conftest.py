"""Configuration of pytest"""
import multiprocessing
from logging import INFO, getLogger, root
from typing import Any, Callable, Generator

import pytest  # type: ignore

collect_ignore = ["setup.py"]


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


@pytest.fixture
def manager_queue() -> Generator[Any, None, None]:
    with multiprocessing.Manager() as manager:
        # Reason: BaseManager's issue.
        yield manager.Queue()  # type: ignore


def configure_log_level() -> None:
    root_logger = getLogger()
    root_logger.setLevel(INFO)


@pytest.fixture
def configurer_log_level() -> Generator[Callable[[], None], None, None]:
    temporary_level = root.level
    yield configure_log_level
    root_logger = getLogger()
    root_logger.setLevel(temporary_level)
