from typing import *

from .types import Rule, ActionDecl, NameDecl, SettingDecl
from .actions import ActionClassProxy
from .scope import ScopeFunc, ScopeDecl


class AppNamespace:
    pass


class Module:
    path: str
    desc: Optional[str]
    apps: AppNamespace = AppNamespace()

    def action_class(self, cls: Any) -> ActionClassProxy:
        return cls

    def action(self, func: Any) -> ActionDecl:
        pass

    def capture(self, rule: Rule) -> Any:
        def __capture(func):
            return func

        return __capture

    def scope(self, func: "ScopeFunc") -> "ScopeDecl":
        return ScopeDecl(mod=self, func=func)

    def setting(
        self,
        name: str,
        type: Type[Any],
        default: Union[Any, SettingDecl.NoValueType] = None,
        desc: str = None,
    ) -> SettingDecl:
        pass

    def list(self, name: str, desc: str = None) -> NameDecl:
        pass

    def mode(self, name: str, desc: str = None) -> NameDecl:
        pass

    def tag(self, name: str, desc: str = None) -> NameDecl:
        pass
