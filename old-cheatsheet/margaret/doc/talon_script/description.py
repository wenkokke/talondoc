from __future__ import annotations
from abc import *
from functools import reduce
from dataclasses import dataclass
from typing import *


@dataclass(frozen=True)
class MissingDocumentation(Exception):
    """Exception raised when a doc string cannot be built"""

    action_name: str


@dataclass(frozen=True)
class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string"""

    lines: tuple[str]


def flatten(descs: Sequence[Description]) -> Description:
    if not descs:
        return Ignore()
    else:
        result = descs[0]
        for desc in descs[1:]:
            result = result.join(desc)
        return result

class Description(ABC):
    def compile(self) -> str:
        """Compiles the Description to a string."""
        return str(self)

    def join(self, other: Description) -> Description:
        """Combines the description with another description."""


@dataclass(frozen=True)
class Chunk(Description):
    """A description of a value or a component of a format string, which can be interpolated into templates."""

    chunk: str

    def __str__(self):
        return self.chunk

    def join(self, other: Description) -> Description:
        if isinstance(other, Chunk):
            return Chunk(f"{self.chunk} {other.chunk}")
        if isinstance(other, Lines) and not other.lines:
            return self  # self.join(Ignore()) == self
        return Line(self).join(other)


@dataclass(frozen=True)
class Template(Description, Callable[[Sequence[Description]], Description]):
    """A description of an action as a template."""

    template: str
    params: tuple[str]

    def __str__(self):
        return self.template

    def __call__(self, args: Sequence[Description]):
        result = self.template
        for param, arg in zip(self.params, args):
            result = result.replace(f"<{param}>", str(arg))
        return Line(result)

    def join(self, other: Description) -> Description:
        return Line(self.template).join(other)


@dataclass(frozen=True)
class Lines(Description):
    """A multiline description, which can no longer be interpolated."""

    lines: tuple[str]

    def compile(self) -> str:
        return "".join(f"{line}. " for line in self.lines)

    def __str__(self):
        """
        Raises:
            InvalidInterpolation: Multiline descriptions should not be interpolated, so this raises an exception.
        """
        raise InvalidInterpolation(self.lines)

    def join(self, other: Description) -> Description:
        if not self.lines:
            return other  # Ignore().join(other) == other
        return Lines((*self.lines, *Line(other).lines))


def Ignore() -> Description:
    """An empty description."""
    return Lines(tuple())


def Line(text: Union[Description, str]) -> Description:
    """Coerce a string or description into a multiline descriptions"""
    if isinstance(text, str):
        return Lines(tuple(text.splitlines()))
    if isinstance(text, Lines):
        return text
    if isinstance(text, Description):
        return Line(str(text))  # Interpolate, then goto next case.
    raise ValueError(f"Unexpected value {text} of type {type(text)}")
