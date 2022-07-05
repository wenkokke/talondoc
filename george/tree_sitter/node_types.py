from dataclasses import dataclass, field, make_dataclass
from functools import reduce
from dataclasses_json import DataClassJsonMixin, dataclass_json
from typing import Callable, ForwardRef, Optional, Type, Union

@dataclass
class Node(DataClassJsonMixin):
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
        if len(types) == 0:
            return None
        elif len(types) == 1:
            return types[0]
        else:
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
    fields: dict[str, NodeArgsType] = field(default_factory=dict)
    children: Optional[NodeArgsType] = None

    def is_terminal(self) -> bool:
        return len(self.fields) == 0 and self.children is None

    def as_type(self, as_cls_name: Callable[[str], str]) -> Type:
        if self.named:
            cls_name = as_cls_name(self.type)
            fields = {}
            if self.fields:
                for field_name, field in self.fields.items():
                    fields[field_name] = field.as_type(as_cls_name=as_cls_name)
            if self.children:
                fields["children"] = self.children.as_type(as_cls_name=as_cls_name)
            fields["text"] = str
            return make_dataclass(
                cls_name=cls_name,
                fields=fields.items(),
                bases=(Node,),
            )
