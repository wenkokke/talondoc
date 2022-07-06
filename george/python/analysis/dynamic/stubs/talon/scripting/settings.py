from george.python.analysis.dynamic import Register
from typing import *
from .types import SettingDecl, SettingValue

class Settings(Register):
    def lookup(self, path: str) -> SettingDecl:
        pass

    def __contains__(self, path: str) -> bool:
        pass

    def __getitem__(self, path: str) -> SettingValue:
        pass

    def get(
        self,
        path: str,
        default: Union[SettingValue, SettingDecl.NoValueType, None] = None,
    ) -> Optional[SettingValue]:
        pass

    def list(self) -> None:
        pass