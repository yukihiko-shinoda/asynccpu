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

See: [Event Loop — Python 3 documentation](https://docs.python.org/3/library/asyncio-eventloop.html)

## Quickstart

### 1. Install

```console
pip install asynccpu
```

### 2. Implement

This package provides `ProcessTaskPoolExecutor` extends [`ProcessPoolExecutor`],
And its instance has the method: `create_process_task()`.

Ex:

```python
import asyncio
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

<!-- markdownlint-disable no-trailing-punctuation -->
## How do I...
<!-- markdownlint-enable no-trailing-punctuation -->

<!-- markdownlint-disable no-trailing-punctuation -->
### Capture log from subprocess?
<!-- markdownlint-enable no-trailing-punctuation -->

Ex:

```python
import asyncio
import multiprocessing
from logging import DEBUG, StreamHandler, Formatter, handlers
from asynccpu import ProcessTaskPoolExecutor


def listener_configurer():
    console_handler = StreamHandler()
    console_handler.setFormatter(Formatter("[%(levelname)s/%(processName)s] %(message)s"))
    # Key Point 4
    return handlers.QueueListener(queue, console_handler)


def worker_configurer():
    root_logger = multiprocessing.getLogger()
    root_logger.setLevel(DEBUG)


with multiprocessing.Manager() as manager:
    # Key Point 2
    queue = manager.Queue()
    listener = listener_configurer()
    listener.start()
    with ProcessTaskPoolExecutor(
        max_workers=3,
        cancel_tasks_when_shutdown=True,
        queue=queue,
        # Key Point 3
        configurer=worker_configurer
    ) as executor:
        futures = {executor.create_process_task(process_cpu_bound, x) for x in range(10)}
        return await asyncio.gather(*futures)
    listener.stop()
```

This implementation is based on following document:

[Logging to a single file from multiple processes | Logging Cookbook — Python 3 documentation]

#### Key Points

1. Inject [`multiprocessing.Queue`] into subprocess
2. Create Queue via [`multiprocessing.Manager`] instance
3. Inject configurer to configure logger for Windows
4. Consider to use [`logging.handlers.QueueListener`]

##### 1. Inject `multiprocessing.Queue` into subprocess

[`logging.handlers.QueueHandler`] is often used for multi-threaded, multi-process code logging.

See: [Logging Cookbook — Python 3.9.2 documentation](https://docs.python.org/3/howto/logging-cookbook.html)

`ProcessTaskPoolExecutor` automatically set `queue` argument into root logger as [`logging.handlers.QueueHandler`] if `queue` argument is set.

##### 2. Create Queue via [`multiprocessing.Manager`] instance

In case of ProcessPoolExecutor, we have to create [`multiprocessing.Queue`] instance via [`multiprocessing.Manager`] instance,
otherwise, following error raised when refer queue argument in child process:

```console
RuntimeError: Queue objects should only be shared between processes through inheritance
```

`ProcessTaskPoolExecutor` extends [`ProcessPoolExecutor`],
therefore it's also required in case when use `ProcessTaskPoolExecutor`.

See: [Using concurrent.futures.ProcessPoolExecutor | Logging Cookbook — Python 3 documentation]

##### 3. Inject configurer to configure logger for Windows

On POSIX, subprocess will share loging configuration with parent process by process fork semantics.
On Windows you can't rely on fork semantics,
so each process requires to run the logging configuration code when it starts.

`ProcessTaskPoolExecutor` will automatically execute `configurer` argument
before starting [`Coroutine`] function.

This design is based on following document:

[Logging to a single file from multiple processes | Logging Cookbook — Python 3 documentation]

For instance, this allows us to set log level in subprocess on Windows.

Note that configuring root logger in subprocess seems to effect parent process on POSIX.

##### 4. Consider to use [`logging.handlers.QueueListener`]

We don't have to create an implementation on the Listener process from scratch, we can use it right away with [`logging.handlers.QueueListener`].

## Credits

This package was created with [Cookiecutter] and the [yukihiko-shinoda/cookiecutter-pypackage] project template.

[`Coroutine`]: https://docs.python.org/3/library/asyncio-task.html#coroutines
[`ProcessPoolExecutor`]: https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor
[`Awaitable`]: https://docs.python.org/3/library/asyncio-task.html#awaitables
[`asyncio`]: https://docs.python.org/3/library/asyncio.html
[`ThreadPoolExecutor`]: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor
[`multiprocessing`]: https://docs.python.org/3/library/multiprocessing.html
[multiprocessing — Process-based parallelism]: https://docs.python.org/3/library/multiprocessing.html
<!-- markdownlint-disable-next-line no-inline-html -->
[Answer: Python multiprocessing PicklingError: Can't pickle <type 'function'> - Stack Overflow]: https://stackoverflow.com/a/8805244/12721873
[Logging to a single file from multiple processes | Logging Cookbook — Python 3 documentation]: https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes
[`multiprocessing.Queue`]: https://docs.python.org/3/library/multiprocessing.html#exchanging-objects-between-processes
[`multiprocessing.Manager`]: https://docs.python.org/3/library/multiprocessing.html#managers
[`logging.handlers.QueueListener`]: https://docs.python.org/3/library/logging.handlers.html#queuelistener
[`logging.handlers.QueueHandler`]: https://docs.python.org/3/library/logging.handlers.html#queuehandler
[Using concurrent.futures.ProcessPoolExecutor | Logging Cookbook — Python 3 documentation]: https://docs.python.org/3/howto/logging-cookbook.html#using-concurrent-futures-processpoolexecutor
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[yukihiko-shinoda/cookiecutter-pypackage]: https://github.com/audreyr/cookiecutter-pypackage
