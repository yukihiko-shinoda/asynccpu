"""Top-level package for Asynchronous CPU."""
from typing import List

from asynccpu.process_task_pool_executor import *  # noqa

__author__ = """Yukihiko Shinoda"""
__email__ = "yuk.hik.future@gmail.com"
__version__ = "1.2.0"

__all__: List[str] = []
# pylint: disable=undefined-variable
__all__ += process_task_pool_executor.__all__  # type: ignore # noqa
