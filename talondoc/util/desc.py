import collections.abc
import dataclasses
import re
import typing

import docstring_parser.google as docstring_google

from ..util.logging import getLogger

_LOGGER = getLogger(__name__)


@dataclasses.dataclass
class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string."""

    argument: typing.Optional["Desc"]
    template: typing.Optional["StepsTemplate"] = None

    def __str__(self) -> str:
        msg = f"Cannot interpolate '{repr(self.argument)}'"
        if self.template:
            msg += f" into template '{repr(self.template)}'"
        return msg


class Desc:
    def as_steps(self) -> "Steps":
        """
        Lift a description to steps.
        """


DescLike = typing.Union[None, str, Desc, collections.abc.Iterable[Desc]]


@dataclasses.dataclass(frozen=True)
class Value(Desc):
    """
    The description of a value.
    """

    desc: str

    def __str__(self) -> str:
        return self.desc

    def as_steps(self) -> "Steps":
        return Steps(steps=(Step(self),))


@dataclasses.dataclass(frozen=True)
class Step(Desc):
    """
    The description of one step in a series of steps.
    """

    desc: typing.Union[str, Value]

    def __str__(self) -> str:
        return str(self.desc)

    def as_steps(self) -> "Steps":
        return Steps(steps=(self,))


@dataclasses.dataclass(frozen=True)
class Steps(Desc):
    """
    The description of a series of steps.
    """

    steps: tuple[Step, ...] = dataclasses.field(default_factory=tuple)

    def __str__(self) -> str:
        return "\n".join(str(step) for step in self.steps)

    def as_steps(self) -> "Steps":
        return self


@dataclasses.dataclass
class StepsTemplate(Desc):
    template: str
    names: tuple[str, ...]

    def __call__(self, values: tuple[typing.Optional[Desc], ...]) -> Steps:
        ret = self.template
        for name, value in zip(self.names, values):
            if isinstance(value, Value):
                ret = ret.replace(f"<{name}>", value.desc)
            else:
                raise InvalidInterpolation(argument=value, template=self)
        return Steps(steps=tuple(Step(desc=desc) for desc in ret.splitlines()))

    def __str__(self):
        return self.template

    def as_steps(self) -> "Steps":
        return Steps(steps=(Step(desc=str(self)),))


def and_then(
    desc1: typing.Optional[Desc], desc2: typing.Optional[Desc]
) -> typing.Optional[Desc]:
    if desc1 is None:
        return desc2
    elif desc2 is None:
        return desc1
    elif isinstance(desc1, Value) and isinstance(desc2, Value):
        return Value(f"{desc1} {desc2}")
    else:
        return Steps(steps=(*desc1.as_steps().steps, *desc2.as_steps().steps))


def concat(*desclike: DescLike) -> typing.Optional[Desc]:
    ret: typing.Optional[Desc] = None
    for desc in desclike:
        if desc is None:
            pass
        elif isinstance(desc, str):
            ret = and_then(ret, Step(desc))
        elif isinstance(desc, Desc):
            ret = and_then(ret, desc)
        else:
            ret = and_then(ret, concat(*desc))
    return ret


def from_docstring(docstring: str) -> typing.Optional[Desc]:
    # Attempt to create a description:
    desc: typing.Optional[Desc]

    # Handle docstrings of the form "Return XXX":
    return_value_desc_en = re.match("^[Rr]eturns? (.*)", docstring)
    if return_value_desc_en:
        desc = Value(desc=return_value_desc_en.group(0))
        return desc

    # Handle Google-style docstrings:
    try:
        # Parse a Google-style docstring:
        doc = docstring_google.parse(docstring)

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

    except docstring_google.ParseError as e:
        pass

    # Treat the docstring as a series of steps:
    desc = concat(*docstring.splitlines())
    return desc
