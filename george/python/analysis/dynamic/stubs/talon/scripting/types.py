from typing import *


SettingValue = Union[float, int, str, List[Any]]
Rule = Any
Capture = Any
Module = Any
Context = Any

class ActionDecl:
    mod: "Module"
    path: str
    default_impl: Optional["ActionImpl"]
    desc: str
    params: Dict[str, str]
    proto: Any


class CaptureDecl:
    mod: "Module"
    path: str
    default_impl: Optional["CaptureImpl"]
    rule: Optional["Rule"]
    desc: str
    type: type
    proto: Any


class NameDecl:
    mod: "Module"
    path: str
    desc: Optional[str]


class AppNamespace:
    def __setitem__(self, key: str, value: str) -> None:
        pass

    def __setattr__(self, key: str, value: str) -> None:
        pass


class AppDecl:
    mod: "Module"
    name: str
    match: "Match"
    cm: "ContextMatch"


class ContextMatch:
    ctx: Union["Context", "Module"]
    match: "Match"


class SettingDecl:
    class NoValueType:
        pass

    NoValue: NoValueType = NoValueType()
    mod: "Module"
    path: str
    type: Type
    default: Union[Any, NoValueType]
    desc: Optional[str]


class ActionImpl:
    ctx: Union["Module", "Context"]
    path: str
    func: Union[Callable, Any]
    type_decl: Optional[ActionDecl]
    type_err: Optional[Any]


class CaptureImpl:
    ctx: Union["Context", "Module"]
    path: str
    rule: Rule
    func: Any


class CommandImpl:
    ctx: "Context"
    rule: Rule
    target: Any
    experiments: set[str]


class ScriptImpl:
    ctx: "Context"
    trigger: str
    script: Any
