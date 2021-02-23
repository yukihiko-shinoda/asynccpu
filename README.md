# Asynchronous CPU

[![Test](https://github.com/yukihiko-shinoda/asynccpu/workflows/Test/badge.svg)](https://github.com/yukihiko-shinoda/asynccpu/actions?query=workflow%3ATest)
[![Test Coverage](https://api.codeclimate.com/v1/badges/897e1ce2259cf3479da8/test_coverage)](https://codeclimate.com/github/yukihiko-shinoda/asynccpu/test_coverage)
[![Maintainability](https://api.codeclimate.com/v1/badges/897e1ce2259cf3479da8/maintainability)](https://codeclimate.com/github/yukihiko-shinoda/asynccpu/maintainability)
[![Code Climate technical debt](https://img.shields.io/codeclimate/tech-debt/yukihiko-shinoda/asynccpu)](https://codeclimate.com/github/yukihiko-shinoda/asynccpu)
[![Updates](https://pyup.io/repos/github/yukihiko-shinoda/asynccpu/shield.svg)](https://pyup.io/repos/github/yukihiko-shinoda/asynccpu/)
[![Python versions](https://img.shields.io/pypi/pyversions/asynccpu.svg)](https://pypi.org/project/asynccpu)
[![Twitter URL](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Fgithub.com%2Fyukihiko-shinoda%2Fasynccpu)](http://twitter.com/share?text=Asynchronous%20CPU&url=https://pypi.org/project/asynccpu/&hashtags=python)

Supports async / await pattern for CPU-bound operations.

## Advantage

1. Support async / await pattern for CPU-bound operations
2. Free from handling event loop

### 1. Support async / await pattern for CPU-bound operations

The async / await syntax makes asynchronous code as:

- Simple
- Readable

This syntax is not only for I/O-bound but also CPU-bound operations.
This package supports [`Coroutine`] function to run in [`ProcessPoolExecutor`] and returns [`Awaitable`] object.

### 2. Free from handling event loop

[`asyncio`] is focusing not CPU-bound but I/O-bound operations.
High-level APIs of [`asyncio`] doesn't support CPU-bound operations
since it works based on not [`ProcessPoolExecutor`] but [`ThreadPoolExecutor`].
When we want to run CPU-bound operations concurrently with [`asyncio`],
we need to use Low-level APIs which need finer control over the event loop behavior.

Application developers should typically use the High-level [`asyncio`] functions, such as asyncio.run(),
and should rarely need to reference Low-level APIs, such as the Event Loop object or call its methods.

See: [Event Loop — Python 3.9.2 documentation](https://docs.python.org/3/library/asyncio-eventloop.html)

## Quickstart

### 1. Install

```console
pip install asynccpu
```

## 2. Implement

This package provides `ProcessTaskPoolExecutor` extends [`ProcessPoolExecutor`],
And its instance has the method: `create_process_task()`.

Ex:

```python
from asynccpu import ProcessTaskPoolExecutor


async def process_cpu_bound(task_id):
    """
    CPU-bound operations will block the event loop:
    in general it is preferable to run them in a process pool.
    """
    return f"task_id: {task_id}, result: {sum(i * i for i in range(10 ** 7))}"


with ProcessTaskPoolExecutor(max_workers=3, cancel_tasks_when_shutdown=True) as executor:
    awaitables = {executor.create_process_task(process_cpu_bound, x) for x in range(10)}
    results = await asyncio.gather(*awaitables)
    for result in results:
        print(result)
```

### Note

The argument of [`Coroutine`] requires not "raw [`Coroutine`] object" but "[`Coroutine`] function"
since raw [`Coroutine`] object is not picklable.

This specification is depend on the one of Python [`multiprocessing`] package:

[multiprocessing — Process-based parallelism]

> Note When an object is put on a queue, the object is pickled
> and a background thread later flushes the pickled data to an underlying pipe.

<!-- markdownlint-disable-next-line no-inline-html -->
See: [Answer: Python multiprocessing PicklingError: Can't pickle <type 'function'> - Stack Overflow]

## Credits

This package was created with [Cookiecutter] and the [yukihiko-shinoda/cookiecutter-pypackage] project template.

[`Coroutine`]: https://docs.python.org/3/library/asyncio-task.html#coroutines
[`ProcessPoolExecutor`]: https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor
[`Awaitable`]: https://docs.python.org/3/library/asyncio-task.html#awaitables
[`asyncio`]: https://docs.python.org/3/library/asyncio.html
[`ThreadPoolExecutor`]: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor
[`multiprocessing`]: https://docs.python.org/3/library/multiprocessing.html
<!-- markdownlint-disable-next-line no-inline-html -->
[Answer: Python multiprocessing PicklingError: Can't pickle <type 'function'> - Stack Overflow]: https://stackoverflow.com/a/8805244/12721873
[multiprocessing — Process-based parallelism]: https://docs.python.org/3/library/multiprocessing.html
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[yukihiko-shinoda/cookiecutter-pypackage]: https://github.com/audreyr/cookiecutter-pypackage
