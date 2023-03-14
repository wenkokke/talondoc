import abc
import dataclasses
from collections.abc import Iterable, Iterator
from typing import Any, ClassVar, Generic, Mapping, Optional, TypeVar, Union

from ...util.logging import getLogger

_LOGGER = getLogger(__name__)

###############################################################################
# Exceptions
###############################################################################


@dataclasses.dataclass(frozen=True)
class DuplicateEntry(Exception):
    """Raised when an entry is defined in multiple modules."""

    entry1: "ObjectEntry"
    entry2: "ObjectEntry"

    def __str__(self) -> str:
        sort = self.entry1.__class__.sort.capitalize()
        name = self.entry1.get_name()
        return "\n".join(
            [
                f"{sort} '{name}' is declared twice:",
                f"- {self.entry1.get_location()}",
                f"- {self.entry2.get_location()}",
            ]
        )


###############################################################################
# Basic Value Types
###############################################################################


ListValue = Union[Mapping[str, Any], Iterable[str]]

SettingValue = Any

EventCode = Union[int, str]


###############################################################################
# Abstract Object Entries
###############################################################################


Entry = TypeVar("Entry", bound="ObjectEntry")


class ObjectEntry(abc.ABC):
    sort: ClassVar[str]

    @property
    def namespace(self) -> str:
        """The top-level namespace for this object, e.g., 'path' for 'path.talon_home'."""
        return self.get_namespace()

    @abc.abstractmethod
    def get_namespace(self) -> str:
        """The top-level namespace for this object, e.g., 'path' for 'path.talon_home'."""

    @property
    def resolved_name(self) -> str:
        """The resolved name for this object, including the top-level namespace."""
        return resolve_name(self.get_name(), namespace=self.namespace)

    @abc.abstractmethod
    def get_name(self) -> str:
        """The name for this object, e.g., 'path.talon_home'."""

    @property
    def qualified_name(self) -> str:
        """The resolved name for this object prefixed by the sort of the object."""
        return f"{self.__class__.sort}:{self.resolved_name}"

    @abc.abstractmethod
    def get_docstring(self) -> Optional[str]:
        """The docstring for the object."""

    @property
    def docstring(self) -> Optional[str]:
        """The docstring for the object."""
        return self.get_docstring()

    @abc.abstractmethod
    def same_as(self, other: "ObjectEntry") -> bool:
        """Test whether or not this object sis the same as the other object."""

    @abc.abstractmethod
    def newer_than(self, other: Union[float, "ObjectEntry"]) -> bool:
        """Test whether or not this object is newer than the other object."""

    @abc.abstractmethod
    def get_location(self) -> str:
        """A string describing the location for this object."""


GroupableObject = TypeVar("GroupableObject", bound="GroupableObjectEntry")


class GroupableObjectEntry(ObjectEntry):
    @abc.abstractmethod
    def group(self: "GroupableObject") -> "GroupEntry":
        """The group to which this object belongs."""

    @abc.abstractmethod
    def is_override(self: "GroupableObject") -> bool:
        """Test whether or not this object is an override."""


@dataclasses.dataclass
class GroupEntry(Generic[GroupableObject]):
    sort: ClassVar[str] = "group"
    default: Optional[GroupableObject] = None
    overrides: list[GroupableObject] = dataclasses.field(default_factory=list)

    @property
    def namespace(self) -> str:
        for entry in self.entries():
            return entry.namespace
        raise ValueError("Empty group")

    @property
    def resolved_name(self) -> str:
        for entry in self.entries():
            return entry.resolved_name
        raise ValueError("Empty group")

    @property
    def docstring(self) -> Optional[str]:
        """The docstring for the object."""
        for entry in self.entries():
            docstring = entry.get_docstring()
            if docstring is not None:
                return docstring
        return None

    def entries(self) -> Iterator[GroupableObject]:
        if self.default is not None:
            yield self.default
        yield from self.overrides

    def append(self, entry: "GroupableObject"):
        assert self.resolved_name == entry.resolved_name, "\n".join(
            [
                f"Cannot append entry with different name to a group:",
                f"- group name: {self.resolved_name}",
                f"- entry name: {entry.resolved_name}",
            ]
        )
        if entry.is_override():
            buffer: list[GroupableObject] = []
            replaced_older: bool = False
            for override in self.overrides:
                if entry.same_as(override):
                    if entry.newer_than(override):
                        replaced_older = True
                        buffer.append(entry)
                    else:
                        replaced_older = True
                        assert entry == override, "\n".join(
                            [
                                f"Found duplicate {entry.__class__.sort}:",
                                f"- {repr(entry)}",
                                f"- {repr(override)}",
                            ]
                        )
                else:
                    buffer.append(override)
            if not replaced_older:
                buffer.append(entry)
            self.overrides = buffer
        else:
            if self.default is not None:
                e = DuplicateEntry(self.default, entry)
                _LOGGER.error(str(e))
            self.default = entry


###############################################################################
# Helper Functions
###############################################################################


def resolve_name(name: str, *, namespace: Optional[str] = None) -> str:
    parts = name.split(".")
    if parts and parts[0] == "self":
        if namespace:
            return ".".join([namespace, *parts[1:]])
        else:
            raise ValueError(f"Cannot resolve 'self' in {name}")
    else:
        return name
