import re
from typing import Iterator, Sequence, Union

from ...registry import Registry
from ...registry import entries as talon


def wildcard_pattern(pattern: str) -> re.Pattern:
    """Compile a pattern with wildcards to a regular expression."""
    return re.compile(".*".join(map(re.escape, pattern.split("*"))))
