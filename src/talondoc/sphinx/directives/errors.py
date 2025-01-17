from collections.abc import Sequence
from dataclasses import dataclass, field


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
                f"{self.location}:"
                f"Multiple matches found for signature '{self.signature}'",
                *map(lambda dsc: f"- {dsc}", self.candidates),
            ]
        )
