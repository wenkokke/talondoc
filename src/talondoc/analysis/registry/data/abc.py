import re
from abc import abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from inspect import Signature
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Union

import editdistance
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from tree_sitter_talon import (
    TalonCapture,
    TalonChoice,
    TalonComment,
    TalonEndAnchor,
    TalonList,
    TalonOptional,
    TalonParenthesizedRule,
    TalonRepeat,
    TalonRepeat1,
    TalonRule,
    TalonSeq,
    TalonStartAnchor,
    TalonWord,
)
from typing_extensions import Self, TypeVar, final

from ...._util.logging import getLogger
from .serialise import (
    JsonValue,
    parse_dict,
    parse_field,
    parse_int,
    parse_optfield,
    parse_str,
)

_LOGGER = getLogger(__name__)


if TYPE_CHECKING:
    from . import Context, File, Module, Package
else:
    Package = type
    File = type
    Module = type
    Context = type


##############################################################################
# Source Locations
##############################################################################


@final
@dataclass(unsafe_hash=True)
class Location:
    path: Path
    start_line: int | None = None
    start_column: int | None = None
    end_line: int | None = None
    end_column: int | None = None

    @staticmethod
    def _str_from_point(line: int | None, column: int | None) -> str | None:
        if line is not None:
            if column is not None:
                return f"{line}:{column}"
            return f"{line}"
        return None

    def __str__(self) -> str:
        resolved_path = self.path.resolve()
        try:
            if resolved_path.is_absolute():
                resolved_path = resolved_path.relative_to(Path.cwd())
        except ValueError as e:
            _LOGGER.warning(e)
        start_position = Location._str_from_point(self.start_line, self.start_column)
        if start_position is not None:
            end_position = Location._str_from_point(self.end_line, self.end_column)
            if end_position is not None:
                return f"{resolved_path}:{start_position}-{end_position}"
            return f"{resolved_path}:{start_position}"
        return f"{resolved_path}"

    @staticmethod
    def from_ast(path: Path, node: Node) -> "Location":
        return Location(
            path=path,
            start_line=node.start_position.line,
            start_column=node.start_position.column,
            end_line=node.end_position.line,
            end_column=node.end_position.column,
        )

    @staticmethod
    def from_function(function: Callable[..., Any]) -> "Location":
        if not callable(function):
            raise TypeError(f"Location.from_function received {function!r}")
        path = Path(function.__code__.co_filename)
        return Location(path=path, start_line=function.__code__.co_firstlineno)

    @staticmethod
    def from_path(path: Path) -> "Location":
        return Location(path=path)

    @staticmethod
    def from_dict(value: JsonValue) -> "Location":
        if isinstance(value, Mapping):
            return Location(
                path=Path(parse_field("path", parse_str)(value)),
                start_line=parse_optfield("start_line", parse_int)(value),
                start_column=parse_optfield("start_column", parse_int)(value),
                end_line=parse_optfield("end_line", parse_int)(value),
                end_column=parse_optfield("end_column", parse_int)(value),
            )
        raise TypeError(f"Expected literal 'builtin' or Location, found {value!r}")

    def to_dict(self) -> JsonValue:
        return asdict(self)


def parse_location(value: JsonValue) -> Union[Literal["builtin"], "Location"]:
    if isinstance(value, str) and value == "builtin":
        return "builtin"
    return Location.from_dict(parse_dict(value))


def asdict_location(location: Union[Literal["builtin"], "Location"]) -> JsonValue:
    if isinstance(location, str) and location == "builtin":
        return "builtin"
    return location.to_dict()


##############################################################################
# Abstact Data
##############################################################################


@dataclass(unsafe_hash=True)
class Data:
    name: str
    description: str | None
    location: Union[None, Literal["builtin"], "Location"]
    parent_name: str | None
    parent_type: type[Package] | type[File] | type[Module] | type[Context] | None
    serialisable: bool

    @property
    def builtin(self) -> bool:
        return self.name.split(".", maxsplit=2)[0] != "user" and (
            not self.parent_name or self.parent_name.split(".", maxsplit=2)[0] != "user"
        )

    def validate(self) -> None:
        if re.match(r"^\s+.*", self.name) or re.match(r".*\s+$", self.name):
            _LOGGER.warning(
                f"{self.location}: "
                f"Leading or trailing whitespace "
                f"in {self.__class__.__name__.lower()} "
                f"name '{self.name}'"
            )
            self.name = self.name.strip()

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.validate()


DataVar = TypeVar("DataVar", bound=Data)


##############################################################################
# Simple Data
##############################################################################


class SimpleData(Data):
    pass


SimpleDataVar = TypeVar(
    "SimpleDataVar",
    bound=SimpleData,
)


##############################################################################
# Grouped Data
##############################################################################


@dataclass(unsafe_hash=True)
class GroupData(Data):
    parent_name: str
    parent_type: type[Module] | type[Context]

    @classmethod
    @abstractmethod
    def from_dict(cls, value: JsonValue) -> Self: ...

    @abstractmethod
    def to_dict(self) -> dict[str, JsonValue]: ...


GroupDataVar = TypeVar(
    "GroupDataVar",
    bound=GroupData,
)


##############################################################################
# Grouped Data with Function
##############################################################################


class GroupDataHasFunction(GroupData):
    function_name: str | None
    function_signature: Signature | None


GroupDataHasFunctionVar = TypeVar(
    "GroupDataHasFunctionVar",
    bound=GroupDataHasFunction,
)

##############################################################################
# Exceptions
##############################################################################


@dataclass(unsafe_hash=True)
class DuplicateData(Exception):
    """Raised when an entry is defined in multiple modules."""

    data: Sequence[Data]

    def __str__(self) -> str:
        cls_names = {data.__class__.__name__ for data in self.data}
        if len(cls_names) >= 2:
            _LOGGER.warning(
                f"DuplicateData exception with types {', '.join(cls_names)}"
            )
        data_names = {data.name for data in self.data}
        if len(data_names) >= 2:
            _LOGGER.warning(
                f"DuplicateData exception with names {', '.join(data_names)}"
            )
        return "\n".join(
            [
                f"{cls_names.pop()} '{data_names.pop()}' is declared multiple times:",
                *[f"- {data.location}" for data in self.data],
            ]
        )


@dataclass(unsafe_hash=True)
class UnknownReference(Exception):
    """Raised when an entry is defined in multiple modules."""

    ref_type: type[Data]
    ref_name: str

    location: str | None = None
    referenced_by: Data | None = None
    known_references: Sequence[str] | None = None

    def __str__(self) -> str:
        buffer = []

        # If location is set, include it:
        if self.location is not None:
            buffer.append(f"{self.location}:")

        # If referenced_by is set, include it:
        if self.referenced_by is not None:
            referenced_by_type_name = self.referenced_by.__class__.__name__.lower()
            buffer.append(
                f"{referenced_by_type_name} '{self.referenced_by.name}' references"
            )

        # Include unknown reference:
        ref_type_name = self.ref_type.__name__.lower()
        buffer.append(f"unknown {ref_type_name} '{self.ref_name}'")

        # If known_references is set, include the closest matching subset:
        if self.known_references:

            def _distance(known_ref_name: str) -> int:
                return int(editdistance.eval(self.ref_name, known_ref_name))

            closest_known_references = sorted(self.known_references, key=_distance)[:10]
            did_you_mean = ", ".join(
                [f"'{ref_name}'" for ref_name in closest_known_references]
            )
            buffer.append(f"(Did you mean {did_you_mean}.)")

        return " ".join(buffer)


##############################################################################
# Convert rules to names
##############################################################################


def _rule_name_escape(text: str) -> str:
    return text.replace("_", "_5f").replace(".", "_2e")


def rule_name(
    rule: (
        TalonRule
        | TalonCapture
        | TalonChoice
        | TalonEndAnchor
        | TalonList
        | TalonOptional
        | TalonParenthesizedRule
        | TalonRepeat
        | TalonRepeat1
        | TalonSeq
        | TalonStartAnchor
        | TalonWord
        | TalonComment
    ),
) -> str:
    def not_comment(rule: object) -> bool:
        return not isinstance(rule, TalonComment)

    match rule:
        case TalonRule(children=children):
            return f"__{'__'.join(map(rule_name, filter(not_comment, children)))}__"
        case TalonCapture(capture_name=capture_name):
            return f"_lt{_rule_name_escape(capture_name.text)}_gt"
        case TalonChoice(children=children):
            return "_pi".join(map(rule_name, filter(not_comment, children)))
        case TalonEndAnchor():
            return "_ra"
        case TalonList(list_name=list_name):
            return f"_lb{_rule_name_escape(list_name.text)}_rb"
        case TalonOptional():
            return f"_ls{rule_name(rule.get_child())}_rs"
        case TalonParenthesizedRule():
            return f"_lp{rule_name(rule.get_child())}_rp"
        case TalonRepeat():
            return f"{rule_name(rule.get_child())}_st"
        case TalonRepeat1():
            return f"{rule_name(rule.get_child())}_pl"
        case TalonSeq(children=children):
            return "__".join(
                map(
                    rule_name,
                    filter(lambda rule: not isinstance(rule, TalonComment), children),
                )
            )
        case TalonStartAnchor():
            return "_la"
        case TalonWord(text=text):
            return _rule_name_escape(text)
        case _:
            raise TypeError(f"Unexpected value {type(rule)}")
