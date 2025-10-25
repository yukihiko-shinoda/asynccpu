"""Top-level package for Asynchronous CPU."""

from __future__ import annotations

from asynccpu.process_task_pool_executor import *  # noqa: F403

__author__ = """Yukihiko Shinoda"""
__email__ = "yuk.hik.future@gmail.com"
__version__ = "1.2.2"

__all__: list[str] = []
__all__ += process_task_pool_executor.__all__  # type:ignore[name-defined] # noqa: F405 pylint: disable=undefined-variable
