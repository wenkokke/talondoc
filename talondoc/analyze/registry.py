import dataclasses
from functools import singledispatchmethod
from typing import ClassVar, Optional
from ..types import FileEntry, ObjectEntry


class NoRegistry(Exception):
    """
    Exception raised when the user attempts to load a talon module outside of
    the 'talon_shims' context manager.
    """


class NoActiveFile(Exception):
    """
    Exception raised when the user attempts to get the active file when no file
    is being processed.
    """


class Registry:
    _active_registry: ClassVar[Optional["Registry"]]

    @staticmethod
    def active() -> "Registry":
        if Registry._active_registry:
            return Registry._active_registry
        else:
            raise NoRegistry()

    @staticmethod
    def activefile() -> FileEntry:
        """
        Retrieve the active file.
        """
        file = Registry.active().get_latest_file()
        if file:
            return file
        else:
            raise NoActiveFile()

    def get_latest_file(self) -> Optional[FileEntry]:
        """
        Get the latest file to be registered.
        """

    def activate(self: Optional["Registry"]):
        Registry._active_registry = self

    def register(self, entry: ObjectEntry):
        """
        Register an object entry.
        """

    def lookup(self, qualified_name: str) -> Optional[ObjectEntry]:
        """
        Look up an object entry by its qualifiedd name.
        """


@dataclasses.dataclass
class Join(Registry):
    registries: list[Registry]

    def get_latest_file(self) -> Optional[FileEntry]:
        for registry in self.registries:
            latest_file = registry.get_latest_file()
            if latest_file:
                return latest_file
        return None

    def register(self, entry: ObjectEntry):
        for registry in self.registries:
            registry.register(entry)

    def lookup(self, qualified_name: str) -> Optional[ObjectEntry]:
        for registry in self.registries:
            entry = registry.lookup(qualified_name)
            if entry:
                return entry
        return None
