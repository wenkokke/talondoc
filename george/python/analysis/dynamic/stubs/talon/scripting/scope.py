from dataclasses import dataclass
from typing import *
from .types import ContextMatch
from .registry import Decls

Module = Any
ScopeFunc = Callable[[], Dict]


@dataclass
class ScopeDecl:
    mod: Module
    func: ScopeFunc

    def update(self, *args) -> None:
        pass


class Scope:
    app_decl: Any
    lock: Any
    registry: Any
    data: Any
    data_sources: Any
    raw_data: Any
    scopes: Any
    registered: Any

    def key(self, path: str) -> Tuple[str, Optional[str]]:
        pass

    def get(self, path: str, default: Any = None) -> Any:
        pass

    def __contains__(self, path: str) -> bool:
        pass

    def __getitem__(self, path: str) -> Any:
        pass

    def matches(self, cm: ContextMatch) -> bool:
        pass

    def update(self, path: str) -> None:
        pass

    def update_one(self, scope: ScopeDecl) -> None:
        pass

    def update_decls(self, decls: Decls) -> None:
        pass