# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`asynccpu` is a Python library that enables async/await patterns for CPU-bound operations using ProcessPoolExecutor. It provides a wrapper around Python's multiprocessing to make concurrent CPU-bound operations feel like async I/O operations.

## Development Commands

This project uses `uv` as the package manager and `invoke` for task automation.

### Testing
- Run fast tests: `uv run pytest -m "not slow"`
- Run all tests: `uv run invoke test.all`
- Run with coverage: `uv run invoke test.coverage`
- Run specific test file: `uv run pytest tests/test_process_task.py`
- Run specific test: `uv run pytest tests/test_file.py::test_function_name`

### Linting
- Fast linting (xenon, ruff, bandit, dodgy, flake8, pydocstyle): `uv run invoke lint.fast`
- Deep linting (mypy, Pylint, semgrep): `uv run invoke lint.deep`
- Individual linters:
  - `uv run invoke lint.ruff`
  - `uv run invoke lint.mypy`
  - `uv run invoke lint.pylint`
  - `uv run invoke lint.flake8`

### Code Formatting
- Format code: `uv run invoke style.fmt`
- Check formatting: `uv run invoke style.fmt --check`

### Building
- Build package: `uv run invoke dist`

### Cleanup
- Clean all artifacts: `uv run invoke clean.all`

## Architecture Overview

### Core Components

1. **ProcessTaskPoolExecutor** ([asynccpu/process_task_pool_executor.py](asynccpu/process_task_pool_executor.py))
   - Extends `concurrent.futures.ProcessPoolExecutor`
   - Main entry point for users - provides `create_process_task()` method
   - Handles process lifecycle, signal handling (SIGTERM), and graceful shutdown
   - Uses `SyncManager` to coordinate process state across parent and child processes
   - Supports logging configuration for subprocesses via `queue` and `configurer` parameters

2. **ProcessTask** ([asynccpu/process_task.py](asynccpu/process_task.py))
   - Lightweight, picklable wrapper around process IDs
   - Hashable to work with collections and tracking structures
   - Uses `psutil.Process` for signal delivery

3. **Subprocess Execution** ([asynccpu/subprocess.py](asynccpu/subprocess.py))
   - `run()`: Entry point function that executes in child processes
   - `Replier`: Context manager that registers/unregisters process from shared dictionary
   - `LoggingInitializer`: Sets up logging infrastructure in child processes
   - Creates new event loop in subprocess and runs coroutine to completion

4. **Process Management Layers**
   - `ProcessTaskFactory`: Creates and tracks individual process tasks
   - `ProcessTaskManager`: Thread-safe task creation with emergency timeout handling

### Key Design Patterns

**Pickling Constraint**: All objects passed to subprocesses must be picklable. This is why:
- Coroutine *functions* are passed, not coroutine *objects*
- ProcessTask stores only process IDs, not psutil.Process instances
- SyncManager is used for shared state (dict, queue)

**Process Tracking**: Parent process maintains a shared dictionary (`SyncManager.dict()`) of active ProcessTask instances. Each subprocess:
1. Registers itself via `Replier.__enter__()`
2. Puts its process ID on a queue to signal readiness
3. Unregisters via `Replier.__exit__()`

**Signal Handling**: The executor intercepts SIGTERM to:
- Send SIGTERM to all tracked child processes (except on Windows)
- Clean up the SyncManager
- Restore original signal handlers
- Windows uses different cancellation strategy (no SIGTERM propagation)

**Logging Support**: Two-part system for capturing subprocess logs:
1. `queue` parameter: Shared queue (created via `multiprocessing.Manager()`) for log records
2. `configurer` parameter: Function executed in each subprocess to configure logging (required on Windows)

## Testing Notes

- Tests use `pytest` with `pytest-asyncio` and `pytest-mock`
- Tests marked with `@pytest.mark.slow` are excluded from fast test runs
- Platform-specific tests exist for Windows vs. POSIX behavior
- Test utilities in [tests/testlibraries/](tests/testlibraries/) provide helpers for process families, keyboard interrupts, etc.

## Code Style

- Maximum line length: 119 characters (Ruff/Pylint), 108 for Flake8
- Import style: Force single-line imports (`from x import y` not `from x import y, z`)
- Docstring convention: Google style
- Type hints: Strict mypy checking enabled
- Python version support: 3.8+

### Import Guidelines

#### Import Placement

- **ALL imports MUST be at the top-level of the file**, immediately after any module comments and docstrings, and before module globals and constants
- **NEVER place imports inside functions, methods, or classes** - this violates PEP 8 and makes dependencies unclear
- **NEVER use conditional imports inside functions** unless absolutely necessary for optional dependencies

#### Import Organization

1. Standard library imports
2. Third-party library imports
3. Local application/library imports

#### Prohibited Patterns

```python
# ❌ NEVER DO THIS - imports inside methods
def test_something():
    import os  # WRONG!
    from pathlib import Path  # WRONG!

# ❌ NEVER DO THIS - imports inside classes
class TestClass:
    def method(self):
        import tempfile  # WRONG!

# ✅ CORRECT - all imports at top
import os
import tempfile
from pathlib import Path

def test_something():
    # Use the imports here
```

Exceptions

- Only use local imports when dealing with circular dependencies or optional dependencies that may not be available
- If you must use local imports, document the reason with a comment

## Important Implementation Details

**Windows vs. POSIX Differences**:
- On Windows, SIGTERM propagates to all processes including parent, so cancellation is handled differently
- Windows requires explicit `configurer` for logging setup (no fork semantics)
- ProcessPoolExecutor behavior differs between platforms

**Subprocess Lifecycle**:
1. Parent creates Future via `create_process_task(coroutine_fn, *args)`
2. Subprocess starts, initializes logging, registers with parent
3. Subprocess creates new event loop and runs coroutine
4. On completion/error, subprocess unregisters and terminates
5. Future resolves in parent

**Emergency Timeout**: ProcessTaskManager uses 1-second timeout for lock acquisition during shutdown to prevent deadlock in edge cases.
