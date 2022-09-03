from collections.abc import Iterable
from typing import Any, Sequence, TypeVar, Union

from docutils import nodes
from sphinx import addnodes

NodeVar = TypeVar("NodeVar", bound=nodes.Node)

AttributeValue = Union[Any, Sequence[Any]]

NodeLike = Union[nodes.Node, Iterable[nodes.Node]]


def _with_children_and_attributes(
    node: NodeVar, *children: NodeLike, **attributes: AttributeValue
) -> NodeVar:
    for child in children:
        if isinstance(child, nodes.Node):
            node += child  # type: ignore
        else:
            for grandchild in child:
                node += grandchild  # type: ignore
    for attribute_name, attribute_value in attributes.items():
        if isinstance(attribute_value, Sequence):
            node[attribute_name].append(attribute_value)  # type: ignore
        else:
            node[attribute_name] = attribute_value  # type: ignore
    return node


def desc_name(*children: NodeLike, **attributes: AttributeValue) -> addnodes.desc_name:
    return _with_children_and_attributes(addnodes.desc_name(), *children, **attributes)


def desc_content(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_content:
    return _with_children_and_attributes(
        addnodes.desc_content(), *children, **attributes
    )


def bullet_list(*children: NodeLike, **attributes: AttributeValue) -> nodes.bullet_list:
    return _with_children_and_attributes(nodes.bullet_list(), *children, **attributes)


def colspec(*children: NodeLike, **attributes: AttributeValue) -> nodes.colspec:
    return _with_children_and_attributes(nodes.colspec(), *children, **attributes)


def entry(*children: NodeLike, **attributes: AttributeValue) -> nodes.entry:
    return _with_children_and_attributes(nodes.entry(), *children, **attributes)


def hlist(*children: NodeLike, **attributes: AttributeValue) -> addnodes.hlist:
    return _with_children_and_attributes(addnodes.hlist(), *children, **attributes)


def paragraph(*children: NodeLike, **attributes: AttributeValue) -> nodes.paragraph:
    return _with_children_and_attributes(nodes.paragraph(), *children, **attributes)


def row(*children: NodeLike, **attributes: AttributeValue) -> nodes.row:
    return _with_children_and_attributes(nodes.row(), *children, **attributes)


def table(*children: NodeLike, **attributes: AttributeValue) -> nodes.table:
    return _with_children_and_attributes(nodes.table(), *children, **attributes)


def tbody(*children: NodeLike, **attributes: AttributeValue) -> nodes.tbody:
    return _with_children_and_attributes(nodes.tbody(), *children, **attributes)


def tgroup(*children: NodeLike, **attributes: AttributeValue) -> nodes.tgroup:
    return _with_children_and_attributes(nodes.tgroup(), *children, **attributes)


def thead(*children: NodeLike, **attributes: AttributeValue) -> nodes.thead:
    return _with_children_and_attributes(nodes.thead(), *children, **attributes)


def title(*children: NodeLike, **attributes: AttributeValue) -> nodes.title:
    return _with_children_and_attributes(nodes.title(), *children, **attributes)
