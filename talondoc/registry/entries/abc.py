import abc
import dataclasses
from collections.abc import Iterable, Iterator
from typing import Any, ClassVar, Generic, Mapping, Optional, TypeVar, Union

import tree_sitter_talon
from typing_extensions import override

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
        sort = self.entry1.__class__.get_sort().capitalize()
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
# Abstract Entries
###############################################################################

AnyEntry = TypeVar("AnyEntry", bound="Entry")


class Entry(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_sort(cls) -> str:
        """Get the sort of the object, e.g., 'action' or 'capture'."""

    @abc.abstractmethod
    def get_namespace(self) -> str:
        """The top-level namespace for this object, e.g., 'path' for 'path.talon_home'."""

    def get_resolved_name(self) -> str:
        """The resolved name for this object, including the top-level namespace."""
        return resolve_name(self.get_name(), namespace=self.get_namespace())

    @abc.abstractmethod
    def get_name(self) -> str:
        """The name for this object, e.g., 'path.talon_home'."""

    @abc.abstractmethod
    def get_qualified_name(self) -> str:
        """The resolved name for this object prefixed by the sort of the object."""

    @abc.abstractmethod
    def get_docstring(self) -> Optional[str]:
        """The docstring for the object."""


AnyObject = TypeVar("AnyObject", bound="ObjectEntry")


class ObjectEntry(Entry):
    @override
    def get_qualified_name(self) -> str:
        return f"{self.__class__.get_sort()}:{self.get_resolved_name()}"

    @abc.abstractmethod
    def same_as(self, other: "ObjectEntry") -> bool:
        """Test whether or not this object sis the same as the other object."""

    @abc.abstractmethod
    def newer_than(self, other: Union[float, "ObjectEntry"]) -> bool:
        """Test whether or not this object is newer than the other object."""

    @abc.abstractmethod
    def get_location(self) -> str:
        """A string describing the location for this object."""


AnyGroupableObject = TypeVar("AnyGroupableObject", bound="GroupableObjectEntry")


class GroupableObjectEntry(ObjectEntry):
    @abc.abstractmethod
    def group(self: "AnyGroupableObject") -> "GroupEntry":
        """The group to which this object belongs."""

    @abc.abstractmethod
    def is_override(self: "AnyGroupableObject") -> bool:
        """Test whether or not this object is an override."""


@dataclasses.dataclass
class GroupEntry(Generic[AnyGroupableObject], Entry):
    default: Optional[AnyGroupableObject] = None
    overrides: list[AnyGroupableObject] = dataclasses.field(default_factory=list)

    @override
    @classmethod
    def get_sort(cls) -> str:
        return "group"

    @override
    def get_namespace(self) -> str:
        for entry in self.entries():
            return entry.get_namespace()
        raise ValueError("Empty group")

    @override
    def get_name(self) -> str:
        for entry in self.entries():
            return entry.get_name()
        raise ValueError("Empty group")

    @override
    def get_resolved_name(self) -> str:
        for entry in self.entries():
            return entry.get_resolved_name()
        raise ValueError("Empty group")

    @override
    def get_qualified_name(self) -> str:
        for entry in self.entries():
            return f"{self.__class__.get_sort()}:{entry.get_qualified_name()}"
        raise ValueError("Empty group")

    @override
    def get_docstring(self) -> Optional[str]:
        for entry in self.entries():
            docstring = entry.get_docstring()
            if docstring is not None:
                return docstring
        return None

    def entries(self) -> Iterator[AnyGroupableObject]:
        if self.default is not None:
            yield self.default
        yield from self.overrides

    def append(self, entry: "AnyGroupableObject"):
        assert self.get_resolved_name() == entry.get_resolved_name(), "\n".join(
            [
                f"Cannot append entry with different name to a group:",
                f"- group name: {self.get_resolved_name()}",
                f"- entry name: {entry.get_resolved_name()}",
            ]
        )
        if entry.is_override():
            buffer: list[AnyGroupableObject] = []
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
                                f"Found duplicate {entry.__class__.get_sort()}:",
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
                _LOGGER.warning(str(e))
            self.default = entry


###############################################################################
# Concrete object types
###############################################################################


class ActionEntry(GroupableObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "action"

    @abc.abstractmethod
    def get_function_name(self) -> Optional[str]:
        """Get the fully qualified name of the underlying function."""


class CaptureEntry(GroupableObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "capture"

    @abc.abstractmethod
    def get_rule(self) -> Union[str, tree_sitter_talon.TalonRule]:
        """Get the underlying rule."""

    @abc.abstractmethod
    def get_function_name(self) -> Optional[str]:
        """Get the fully qualified name of the underlying function."""


class ListEntry(GroupableObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "list"

    @abc.abstractmethod
    def get_value(self) -> Optional[ListValue]:
        """Get the underlying value."""


class ModeEntry(ObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "mode"


class SettingEntry(GroupableObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "setting"

    @abc.abstractmethod
    def get_value_type(self) -> Optional[str]:
        """Get the type of the underlying value."""

    @abc.abstractmethod
    def get_value(
        self,
    ) -> Optional[Union[SettingValue, tree_sitter_talon.TalonExpression]]:
        """Get the underlying value."""


class TagEntry(ObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "tag"


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
