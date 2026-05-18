"""This module implements exceptions for this package."""

# Tis comment avoids docformatter's issue:
# - The docformatter removes blank line against PEP8 (conflicts with Ruff (Black)) · Issue #350 · PyCQA/docformatter
#   https://github.com/PyCQA/docformatter/issues/350


class Error(Exception):
    """Base class for exceptions in this module.

    @see https://docs.python.org/3/tutorial/errors.html#user-defined-exceptions
    """


# Reason: This is not exception in business logic.
class Terminated(Error):  # noqa: N818
    """Terminated."""
