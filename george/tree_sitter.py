from dataclasses import dataclass, field, make_dataclass
from functools import reduce
from dataclasses_json import DataClassJsonMixin, dataclass_json
from pathlib import Path
from tree_sitter import Tree
from typing import Callable, ForwardRef, Optional, Type, TypeVar, Union
import tree_sitter as ts


def _snake_to_pascal(text: str) -> str:
    return "".join(chunk.capitalize() for chunk in text.split("_"))


A = TypeVar("A", bound="TreeSitterNode")


class TreeSitterNode(DataClassJsonMixin):
    @classmethod
    def from_node(cls: Type[A], node: ts.Node) -> A:
        pass


@dataclass_json
@dataclass
class SimpleNodeType:
    type: str
    named: bool

    def as_type(self, as_cls_name: Callable[[str], str]) -> Optional[Type]:
        if self.named:
            return ForwardRef(as_cls_name(self.type))

    @staticmethod
    def list_as_type(
        simple_node_types: list["SimpleNodeType"],
        as_cls_name: Callable[[str], str],
    ) -> Type:
        types = [
            simple_node_type.as_type(as_cls_name=as_cls_name)
            for simple_node_type in simple_node_types
            if simple_node_type.named
        ]
        match types:
            case []:
                return None
            case [T]:
                return T
            case types:
                return reduce(lambda R, T: Union[R, T], types)


@dataclass_json
@dataclass
class NodeArgsType:
    multiple: bool
    required: bool
    types: list[SimpleNodeType]

    def as_type(
        self,
        as_cls_name: Callable[[str], str],
    ) -> Type:
        type = SimpleNodeType.list_as_type(self.types, as_cls_name=as_cls_name)
        if self.multiple:
            return list[type]
        else:
            if self.required:
                return type
            else:
                return Optional[type]


@dataclass_json
@dataclass
class NodeType:
    type: str
    named: bool
    fields: Optional[dict[str, NodeArgsType]] = None
    children: Optional[NodeArgsType] = None

    def is_terminal(self) -> bool:
        return self.fields is None and self.children is None

    def as_type(self, as_cls_name: Callable[[str], str]) -> Type:
        if self.named:
            cls_name = as_cls_name(self.type)
            fields = {}
            if self.fields:
                for field_name, field in self.fields.items():
                    fields[field_name] = field.as_type(as_cls_name=as_cls_name)
            if self.children:
                fields["children"] = self.children.as_type(as_cls_name=as_cls_name)
            if self.is_terminal():
                fields["text"] = str
            return make_dataclass(
                cls_name=cls_name,
                fields=fields.items(),
                bases=(TreeSitterNode,),
                frozen=True,
            )


def TypeProvider(
    cls_name: str,
    node_types: list[NodeType],
    as_cls_name: Callable[[str], str] = _snake_to_pascal,
):
    # Convert <node_type.type> to qualified class name
    as_cls_qualname = lambda text: f"{cls_name}.{as_cls_name(text)}"

    # Dictionary of dataclasses for named nodes
    NodeClasses = {
        as_cls_name(node_type.type): node_type.as_type(as_cls_name=as_cls_qualname)
        for node_type in node_types
        if node_type.named
    }
    AnyNodeClass = Union[
        ForwardRef(f"{cls_name}.Error"),
        SimpleNodeType.list_as_type(node_types, as_cls_name=as_cls_qualname),
    ]

    # Error node dataclass
    @dataclass_json
    @dataclass
    class Error:
        children: list[AnyNodeClass]

    NodeClasses["ERROR"] = Error

    # Dictionary of node types for named nodes
    named_node_types: dict[str, NodeType] = {
        node_type.type: node_type for node_type in node_types if node_type.named
    }

    @staticmethod
    def parse(node: ts.Node) -> Type[AnyNodeClass]:
        """
        Convert a tree-sitter Node to an instance of a generated dataclass.
        """
        if node.is_named:
            if node.type == "ERROR":
                return Error(
                    children=[parse(child) for child in node.children if child.is_named]
                )
            else:
                node_type = named_node_types[node.type]
                fields = {}
                if node_type.fields:
                    for field_name, _ in node_type.fields.items():
                        fields[field_name] = parse(node.child_by_field_name(field_name))
                if node_type.children:
                    fields["children"] = [
                        parse(child)
                        for child in node.children
                        if child.is_named and not child in fields.values()
                    ]
                if node_type.is_terminal():
                    fields["text"] = node.text.decode()
                return NodeClasses[as_cls_name(node.type)](**fields)

    return type(cls_name, (object,), NodeClasses | {"parse": parse})
