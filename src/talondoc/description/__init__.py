import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Optional

import docstring_parser

from .._util.logging import getLogger

_LOGGER = getLogger(__name__)


@dataclass
class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string."""

    argument: Optional["Description"]
    template: Optional["StepsTemplate"] = None

    def __str__(self) -> str:
        msg = f"Cannot interpolate '{self.argument!r}'"
        if self.template:
            msg += f" into template '{self.template!r}'"
        return msg


class Description:
    def as_steps(self) -> "Steps":
        """
        Lift a description to steps.
        """
        return Steps(())


DescLike = None | str | Description | Iterable[Description]


@dataclass
class Value(Description):
    """
    The description of a value.
    """

    desc: str

    def __str__(self) -> str:
        return self.desc

    def as_steps(self) -> "Steps":
        return Steps(steps=(Step(self),))


@dataclass
class Step(Description):
    """
    The description of one step in a series of steps.
    """

    desc: str | Value

    def __str__(self) -> str:
        return str(self.desc)

    def as_steps(self) -> "Steps":
        return Steps(steps=(self,))


@dataclass
class Steps(Description):
    """
    The description of a series of steps.
    """

    steps: Sequence[Step] = field(default_factory=tuple)

    def __str__(self) -> str:
        return "\n".join(str(step) for step in self.steps)

    def as_steps(self) -> "Steps":
        return self


@dataclass
class StepsTemplate(Description):
    template: str
    names: Sequence[str]

    def __call__(self, values: Sequence[Description | None]) -> Steps:
        ret = self.template
        for name, value in zip(self.names, values, strict=False):
            if isinstance(value, Value):
                ret = ret.replace(f"<{name}>", value.desc)
            else:
                raise InvalidInterpolation(argument=value, template=self)
        return Steps(steps=tuple(Step(desc=desc) for desc in ret.splitlines()))

    def __str__(self) -> str:
        return self.template

    def as_steps(self) -> "Steps":
        return Steps(steps=(Step(desc=str(self)),))


def and_then(
    desc1: Description | None, desc2: Description | None
) -> Description | None:
    if desc1 is None:
        return desc2
    elif desc2 is None:
        return desc1
    elif isinstance(desc1, Value) and isinstance(desc2, Value):
        return Value(f"{desc1} {desc2}")
    else:
        return Steps(steps=(*desc1.as_steps().steps, *desc2.as_steps().steps))


def concat(*desclike: DescLike) -> Description | None:
    ret: Description | None = None
    for desc in desclike:
        if desc is None:
            pass
        elif isinstance(desc, str):
            ret = and_then(ret, Step(desc))
        elif isinstance(desc, Description):
            ret = and_then(ret, desc)
        else:
            ret = and_then(ret, concat(*desc))
    return ret


def from_docstring(docstring: str) -> Description | None:
    # Attempt to create a description:
    desc: Description | None

    # Handle docstrings of the form "Return XXX":
    return_value_desc_en = re.match("^[Rr]eturns? (.*)", docstring)
    if return_value_desc_en:
        desc = Value(desc=return_value_desc_en.group(0))
        return desc

    # Handle Google-style docstrings:
    try:
        # Parse a Google-style docstring:
        doc = docstring_parser.parse(docstring)

        # Actions which document their parameters become
        # step templates that can interpolate their arguments:
        if doc.short_description and len(doc.params) > 0:
            desc = StepsTemplate(
                template=doc.short_description,
                names=tuple(param.arg_name for param in doc.params),
            )
            return desc

        # Actions which document their return values become
        # value descriptions that can be used inline:
        if doc.returns and doc.returns.description:
            desc = Value(desc=doc.returns.description)
            return desc

    except docstring_parser.ParseError:
        pass

    # Treat the docstring as a series of steps:
    desc = concat(*docstring.splitlines())
    return desc
