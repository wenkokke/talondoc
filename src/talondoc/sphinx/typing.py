from collections.abc import Callable, Sequence
from typing import TypeAlias

from typing_extensions import NotRequired, Required, TypedDict

TalonEvent = str


class TalonPackage(TypedDict):
    path: Required[str]
    name: NotRequired[str]
    include: NotRequired[str | Sequence[str]]
    exclude: NotRequired[str | Sequence[str]]
    trigger: NotRequired[TalonEvent | Sequence[TalonEvent]]


TalonDocstringHook_Callable: TypeAlias = Callable[[str, str], str | None]
TalonDocstringHook_Dict: TypeAlias = dict[str, dict[str, str]]


TalonDocstringHook: TypeAlias = TalonDocstringHook_Callable | TalonDocstringHook_Dict
