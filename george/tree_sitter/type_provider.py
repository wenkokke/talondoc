from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Any, Callable, Union
from .node_types import NodeType, Node
import tree_sitter as ts


def _snake_to_pascal(text: str) -> str:
    return "".join(chunk.capitalize() for chunk in text.split("_"))


def TypeProvider(
    cls_name: str,
    node_types: list[NodeType],
    as_cls_name: Callable[[str], str] = _snake_to_pascal,
):
    # Dictionary of dataclasses for named nodes
    NodeClasses = {
        as_cls_name(node_type.type): node_type.as_type(as_cls_name=as_cls_name)
        for node_type in node_types
        if node_type.named
    }

    # Error node dataclass
    @dataclass_json
    @dataclass
    class ERROR(Node):
        children: list[Node]

    NodeClasses[as_cls_name("ERROR")] = ERROR

    # Dictionary of node types for named nodes
    named_node_types: dict[str, NodeType] = {
        node_type.type: node_type for node_type in node_types if node_type.named
    }

    @staticmethod
    def from_tree_sitter(node: ts.Node) -> Node:
        """
        Convert a tree-sitter Node to an instance of a generated dataclass.
        """
        if node.is_named:
            if node.type == "ERROR":
                return ERROR(
                    children=[
                        from_tree_sitter(child)
                        for child in node.children
                        if child.is_named
                    ]
                )
            else:
                node_type = named_node_types[node.type]
                fields = {}
                if node_type.fields:
                    for field_name, _ in node_type.fields.items():
                        fields[field_name] = from_tree_sitter(
                            node.child_by_field_name(field_name)
                        )
                if node_type.children:
                    fields["children"] = [
                        from_tree_sitter(child)
                        for child in node.children
                        if child.is_named and not child in fields.values()
                    ]
                fields["text"] = node.text.decode()
                return NodeClasses[as_cls_name(node.type)](**fields)

    def node_name(node_or_type: Union[Node, NodeType]) -> str:
        if isinstance(node_or_type, Node):
            node_type_name_parts = node_or_type.__class__.__name__.split(".")
            if node_type_name_parts[0] == cls_name:
                node_type_name_parts = node_type_name_parts[1:]
            node_type_name = ".".join(node_type_name_parts)
        if isinstance(node_or_type, NodeType):
            node_type_name = as_cls_name(node_or_type.type)
        return node_type_name

    def visit(self, node: Node):
        if isinstance(node, Node):
            visit_node_type = getattr(self, f"visit_{node_name(node)}")
            visit_node_type(node)

    def generic_visit(self, node: Node):
        for dataclass_field_name, _ in node.__dataclass_fields__.items():
            field = getattr(node, dataclass_field_name)
            if isinstance(field, list):
                for item in field:
                    self.visit(item)
            if isinstance(field, Node):
                self.visit(field)

    NodeVisitor = type(
        "NodeVisitor",
        (object,),
        {"visit": visit, "generic_visit": generic_visit, "visit_ERROR": generic_visit}
        | {
            f"visit_{node_name(node_type)}": generic_visit
            for node_type in named_node_types.values()
        },
    )

    def transform(self, node: Node) -> Any:
        if isinstance(node, Node):
            func = getattr(self, f"transform_{node_name(node)}")
            kwargs = {}
            for field_name in node.__dataclass_fields__.keys():
                field = getattr(node, field_name)
                if isinstance(field, Node):
                    kwargs[field_name] = self.transform(field)
                    kwargs[f"{field_name}_hist"] = field
                elif isinstance(field, list):
                    kwargs[field_name] = []
                    kwargs[f"{field_name}_hist"] = []
                    for field_item in field:
                        kwargs[field_name].append(self.transform(field_item))
                        kwargs[f"{field_name}_hist"].append(field_item)
                else:
                    kwargs[field_name] = field
            return func(**kwargs)
        else:
            return ValueError(node)

    NodeTransformer = type(
        "NodeTransformer",
        (object,),
        {"transform": transform},
    )

    return type(
        cls_name,
        (object,),
        NodeClasses
        | {"NodeVisitor": NodeVisitor}
        | {"NodeTransformer": NodeTransformer}
        | {"from_tree_sitter": from_tree_sitter},
    )
