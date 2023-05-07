from dataclasses import dataclass
from typing import Any, List


@dataclass
class UnmatchedSignature(Exception):
    """
    Exception raised when multiple objects match the given signature.
    """

    loc: str
    sig: str

    def __str__(self) -> str:
        return f"{self.loc}: No match found for signature '{self.sig}'"


@dataclass
class AmbiguousSignature(Exception):
    """
    Exception raised when multiple objects match the given signature.
    """

    loc: str
    sig: str
    lst: List[str]

    def __str__(self) -> str:
        return "\n".join(
            [
                f"{self.loc}: Multiple matches found for signature '{self.sig}'",
                *map(lambda dsc: f"- {dsc}", self.lst),
            ]
        )
