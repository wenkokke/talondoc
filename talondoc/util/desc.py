import collections.abc
import dataclasses
import re
import typing
import docstring_parser.google as docstring_google


class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string"""


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


DescLike = typing.Union[None, str, Desc, collections.abc.Iterable[DescLike]]  # type: ignore


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
            result = result.replace(f"<{name}>", str(value))
        return Step(desc=result)

    def __str__(self):
        return self.template

    def compile(self) -> str:
        return str(self)


def lift(desc: typing.Union[str, Desc]) -> Steps:
    if isinstance(desc, str):
        return Steps((Step(desc),))
    elif isinstance(desc, Value):
        return Steps((Step(desc),))
    elif isinstance(desc, Step):
        return Steps((desc,))
    elif isinstance(desc, StepTemplate):
        return Steps((Step(str(desc)),))
    elif isinstance(desc, Steps):
        return desc
    else:
        raise TypeError(type(desc))


def concat(*desclike: DescLike) -> typing.Optional[Desc]:
    accumulator: typing.Optional[Desc] = None
    for desc in desclike:
        if isinstance(desc, Value):
            accumulator = accumulator + desc
        elif isinstance(desc, collections.abc.Iterable):
            accumulator = concat(accumulator, *desc)
        elif desc is not None:
            accumulator = concat(accumulator, lift(desc))
    return accumulator


def from_docstring(docstring: str) -> typing.Optional[Desc]:
    # Handle docstrings of the form "Return XXX":
    is_return = re.match("^[Rr]eturns? (.*)", docstring)
    if is_return:
        return Value(desc=is_return.group(0))

    # Handle Google-style docstrings:
    try:
        # Actions which document their parameters
        # become description templates:
        doc = docstring_google.parse(docstring)
        if doc.short_description and doc.params:
            return StepTemplate(
                template=doc.short_description,
                names=tuple(param.arg_name for param in doc.params),
            )
        # Actions which document their return values
        # become descriptions that can be used inline:
        if doc.returns and doc.returns.description:
            return Value(desc=doc.returns.description)

    except docstring_google.ParseError:
        pass

    # Treat the docstring as a series of steps:
    return concat(*docstring.splitlines())
