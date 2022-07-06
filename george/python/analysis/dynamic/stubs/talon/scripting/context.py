from typing import *

from .actions import ActionClassProxy
from .types import CommandImpl, ScriptImpl, SettingValue


class Context:
    name: str
    path: str
    desc: Optional[str]

    def action_class(self, path: str) -> Callable[[Any], ActionClassProxy]:
        def __decorator(cls):
            return cls

        return __decorator

    def action(self, path: str):
        def __action(*args):
            pass

        return __action

    def capture(self, path: str = None, *, rule: str = None) -> Any:
        def __decorator(func):
            return func

        return __decorator

    @property
    def matches(self) -> Union[str, "Match"]:
        return ""

    @matches.setter
    def matches(self, matches: Union[str, "Match"]):
        pass

    @property
    def apps(self):
        pass

    @apps.setter
    def apps(self, value: Sequence[str]):
        return []

    @property
    def lists(self) -> dict[str, Mapping[str, str]]:
        return {}

    @lists.setter
    def lists(self, lists: dict[str, Union[dict[str, str], Sequence[str]]]) -> None:
        pass

    @property
    def settings(self):
        return {}

    @settings.setter
    def settings(self, value: dict[str, SettingValue]):
        pass

    @property
    def tags(self):
        pass

    @tags.setter
    def tags(self, value: Sequence[str]):
        pass

    @property
    def commands(self) -> Mapping[str, CommandImpl]:
        pass

    @property
    def hotkeys(self) -> Mapping[str, ScriptImpl]:
        pass

    @property
    def noises(self):
        pass

    def __hash__(self) -> int:
        pass

    def __eq__(self, other: Any) -> bool:
        pass

    def __ne__(self, other: Any) -> bool:
        pass

    def __lt__(self, other: Any) -> bool:
        pass

    def __gt__(self, other: Any) -> bool:
        pass
