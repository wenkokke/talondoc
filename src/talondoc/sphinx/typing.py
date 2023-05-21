from collections.abc import Callable, Sequence
from typing import Optional, Union

from typing_extensions import NotRequired, Required, TypeAlias, TypedDict

TalonEvent = str

TalonPackage = TypedDict(
    "TalonPackage",
    {
        "path": Required[str],
        "name": NotRequired[str],
        "include": NotRequired[Union[str, Sequence[str]]],
        "exclude": NotRequired[Union[str, Sequence[str]]],
        "trigger": NotRequired[Union[TalonEvent, Sequence[TalonEvent]]],
    },
)

TalonDocstringHook_Callable: TypeAlias = Callable[[str, str], Optional[str]]
TalonDocstringHook_Dict: TypeAlias = dict[str, dict[str, str]]


TalonDocstringHook: TypeAlias = Union[
    TalonDocstringHook_Callable,
    TalonDocstringHook_Dict,
]
