"""Types."""

# Reason: This file only is read when type checking.
from typing import TYPE_CHECKING  # pragma: no cover
from typing import ParamSpec  # pragma: no cover

if TYPE_CHECKING:
    from typing import TypeVar

    TypeVarReturnValue = TypeVar("TypeVarReturnValue")
    ParamSpecCoroutineFunctionArguments = ParamSpec("ParamSpecCoroutineFunctionArguments")
