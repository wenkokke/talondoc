from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string"""

    desc: "Desc"


class Desc(ABC):
    def __add__(self, other: "Desc") -> "Desc":
        """
        Combine two descriptions.
        """

    def compile(self) -> str:
        """
        Compile a description to a string.
        """


@dataclass(frozen=True)
class Ignore(Desc):
    def __add__(self, other: "Desc") -> "Desc":
        return other

    def compile(self) -> str:
        return ""


@dataclass(frozen=True)
class Chunk(Desc):
    text: str

    def __add__(self, other: "Desc") -> "Desc":
        if isinstance(other, Ignore):
            return self
        if isinstance(other, Chunk):
            return Chunk(text=f"{self.text} {other.text}")
        if isinstance(other, Lines):
            return Lines(lines=(self.text, *other.lines))

    def __str__(self):
        return self.text

    def compile(self) -> str:
        return self.text


@dataclass(frozen=True)
class Lines(Desc):
    lines: tuple[Desc, ...]

    def __str__(self):
        """
        Raises:
            InvalidInterpolation: Multiline descriptions should not be interpolated, so this raises an exception.
        """
        raise InvalidInterpolation(self.lines)

    def compile(self) -> str:
        return "\n".join(line.compile() for line in self.lines)


def Line(text: str) -> Desc:
    return Lines(lines=[Chunk(text=text)])


@dataclass(frozen=True)
class Template(Desc):
    template: str
    params: tuple[str, ...]

    def __call__(self, arguments: tuple[Desc, ...]):
        result = self.template
        for param, arg in zip(self.params, arguments):
            result = result.replace(f"<{param}>", str(arg))
        return Line(result)

    def __str__(self):
        return self.template

    def compile(self) -> str:
        return self.template
