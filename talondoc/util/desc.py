import collections.abc
import dataclasses
import re
import typing

import docstring_parser.google as docstring_google

from ..util.logging import getLogger

_logger = getLogger(__name__)


@dataclasses.dataclass
class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string."""

    argument: "Desc"
    template: typing.Optional["StepTemplate"] = None

    def __str__(self) -> str:
        msg = f"Cannot interpolate '{repr(self.argument)}'"
        if self.template:
            msg += f" into template '{repr(self.template)}'"
        return msg


class Desc:
    def __add__(self, other: typing.Optional["Desc"]) -> "Desc":
        """
        Combine two descriptions.
        """
        return self if other is None else lift(self) + lift(other)

    def __radd__(self, other: typing.Optional["Desc"]) -> "Desc":
        """
        Combine two descriptions, reversed.
        """
        return self if other is None else lift(other) + lift(self)

    def compile(self) -> str:
        """
        Compile a description to a string.
        """


DescLike = typing.Union[None, str, Desc, collections.abc.Iterable["DescLike"]]  # type: ignore


@dataclasses.dataclass(frozen=True)
class Value(Desc):
    """
    The description of a value.
    """

    desc: str

    def compile(self) -> str:
        return self.desc

    def __add__(self, other: typing.Optional[Desc]) -> Desc:
        if isinstance(other, Value):
            return Value(f"{self.desc} {other.desc}")
        return super().__add__(other)

    def __str__(self) -> str:
        return self.compile()


@dataclasses.dataclass(frozen=True)
class Step(Desc):
    """
    The description of one step in a series of steps.
    """

    desc: typing.Union[str, Value]

    def compile(self) -> str:
        return str(self.desc)

    def __str__(self) -> str:
        raise InvalidInterpolation(self)


@dataclasses.dataclass(frozen=True)
class Steps(Desc):
    """
    The description of a series of steps.
    """

    steps: tuple[Step, ...] = dataclasses.field(default_factory=tuple)

    def compile(self) -> str:
        return "\n".join(step.compile() for step in self.steps)

    def __str__(self) -> str:
        raise InvalidInterpolation(self)


@dataclasses.dataclass
class StepTemplate(Desc):
    template: str
    names: tuple[str, ...]

    def __call__(self, values: tuple[Value, ...]):
        result = self.template
        for name, value in zip(self.names, values):
            try:
                result = result.replace(f"<{name}>", str(value))
            except InvalidInterpolation as e:
                e.template = self
                raise e
        return Step(desc=result)

    def __str__(self):
        return self.template

    def compile(self) -> str:
        return str(self)


def lift(desc: typing.Union[str, Desc]) -> Steps:
    if isinstance(desc, str):
        return Steps((Step(desc),))
    elif isinstance(desc, Value):
        return Steps((Step(desc.compile()),))
    elif isinstance(desc, Step):
        return Steps((desc,))
    elif isinstance(desc, StepTemplate):
        return Steps((Step(desc.compile()),))
    elif isinstance(desc, Steps):
        return desc
    else:
        raise TypeError(type(desc))


def concat(*desclike: DescLike) -> typing.Optional[Desc]:
    accumulator: typing.Optional[Desc] = None
    for desc in desclike:
        if desc is None:
            pass
        elif isinstance(desc, Value):
            accumulator = accumulator + desc
        elif isinstance(desc, (str, Step, StepTemplate, Steps)):
            accumulator = accumulator + lift(desc)
        else:
            assert not isinstance(desc, Desc)
            accumulator = concat(accumulator, *desc)
    return accumulator


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
            desc = StepTemplate(
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
