import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass
class AmbiguousSignature(Exception):
    """
    Exception raised when multiple objects match the given signature.
    """

    location: str
    signature: str
    candidates: Sequence[str] = field(default_factory=tuple)

    def _resolved_location(self) -> str:
        path, rest = self.location.split(":", maxsplit=2)
        return f"{Path(path).resolve(strict=False)}:{rest}"

    def __str__(self) -> str:
        return "\n".join(
            [
                f"{self._resolved_location()}:"
                f"Multiple matches found for signature '{self.signature}'",
                *map(lambda dsc: f"- {dsc}", self.candidates),
            ]
        )
