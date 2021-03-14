"""Configuration of pytest"""
import multiprocessing
from logging import INFO, Logger, getLogger, root

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
def manager_queue():
    with multiprocessing.Manager() as manager:
        yield manager.Queue()


def configure_log_level() -> Logger:
    root_logger = getLogger()
    root_logger.setLevel(INFO)


@pytest.fixture
def configurer_log_level():
    temporary_level = root.level
    yield configure_log_level
    root_logger = getLogger()
    root_logger.setLevel(temporary_level)
