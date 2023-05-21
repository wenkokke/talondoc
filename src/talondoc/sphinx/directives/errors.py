from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class AmbiguousSignature(Exception):
    """
    Exception raised when multiple objects match the given signature.
    """

    location: str
    signature: str
    candidates: Sequence[str] = field(default_factory=tuple)

    def __str__(self) -> str:
        return "\n".join(
            [
                f"{self.location}: Multiple matches found for signature '{self.signature}'",
                *map(lambda dsc: f"- {dsc}", self.candidates),
            ]
        )
