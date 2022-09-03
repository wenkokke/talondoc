import dataclasses
from typing import ClassVar, Optional

from ..entries import FileEntry, ObjectEntry


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
        file = Registry.active().currentfile
        if file:
            return file
        else:
            raise NoActiveFile()

    @property
    def currentfile(self) -> Optional[FileEntry]:
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
