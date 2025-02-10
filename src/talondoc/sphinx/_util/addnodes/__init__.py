from collections.abc import Iterable, Sequence
from inspect import Parameter, Signature
from typing import Any, TypeVar

from docutils import nodes
from sphinx import addnodes

from ...._util.builtin import (
    builtin_number_types,
    builtin_type_names,
    builtin_types,
    is_builtin_string_type,
)
from ...._util.logging import getLogger
from ....analysis.static.python.shims import ObjectShim
from . import fragtable as morenodes

_LOGGER = getLogger(__name__)

################################################################################
# Type Aliases
################################################################################

NodeVar = TypeVar("NodeVar", bound=nodes.Node)

AttributeValue = Any | Sequence[Any]

NodeLike = nodes.Node | Iterable[nodes.Node]

################################################################################
# Functional Wrappers around Sphinx node types
################################################################################


def _with_children_and_attributes(
    node: NodeVar, *children: NodeLike, **attributes: AttributeValue
) -> NodeVar:
    for child in children:
        if isinstance(child, nodes.Node):
            node += child  # type: ignore[operator]
        else:
            for grandchild in child:
                node += grandchild  # type: ignore[operator]
    for attribute_name, attribute_value in attributes.items():
        if isinstance(attribute_value, Sequence):
            node[attribute_name].append(attribute_value)  # type: ignore[index]
        else:
            node[attribute_name] = attribute_value  # type: ignore[index]
    return node


def desc_name(*children: NodeLike, **attributes: AttributeValue) -> addnodes.desc_name:
    return _with_children_and_attributes(addnodes.desc_name(), *children, **attributes)


def desc_addname(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_addname:
    return _with_children_and_attributes(
        addnodes.desc_addname(), *children, **attributes
    )


def desc_qualname(
    signode: addnodes.desc_signature, qualname: str, **attributes: AttributeValue
) -> addnodes.desc_signature:
    parts = list(qualname.split("."))
    parts.reverse()
    children: list[NodeLike] = []
    children.append(desc_name(nodes.Text(parts.pop(0)), **attributes))
    for part in parts:
        children.append(desc_addname(nodes.Text(f"{part}."), **attributes))
    children.reverse()
    for child in children:
        signode += child
    return signode


def desc_type(annotation: Any, **attributes: AttributeValue) -> addnodes.desc_type:
    children: list[NodeLike] = []
    if isinstance(annotation, ObjectShim):
        children.append(nodes.Text("..."))
    elif isinstance(annotation, type):
        if issubclass(annotation, ObjectShim):
            children.append(nodes.Text("..."))
        elif annotation in builtin_types:
            children.append(desc_sig_keyword_type(nodes.Text(annotation.__name__)))
        else:
            children.append(nodes.Text(annotation.__name__))
    elif annotation.__class__.__name__ == "_UnionGenericAlias":
        # NOTE: typing.Union is wild
        if hasattr(annotation, "__args__"):
            args: list[NodeLike] = []
            for arg in annotation.__args__:
                args.append(desc_type(arg))
            if args:
                children.append(args.pop(0))
                for arg in args:
                    children.append(desc_sig_space())
                    children.append(desc_sig_operator(nodes.Text("|")))
                    children.append(desc_sig_space())
                    children.append(arg)
        else:
            children.append(nodes.Text(str(annotation)))
    elif isinstance(annotation, str):
        if annotation in builtin_type_names:
            children.append(desc_sig_keyword_type(nodes.Text(annotation)))
        else:
            children.append(nodes.Text(annotation))
    else:
        children.append(nodes.Text(repr(annotation)))
    return _with_children_and_attributes(addnodes.desc_type(), *children, **attributes)


def desc_literal(value: Any, **attributes: AttributeValue) -> addnodes.desc_sig_element:
    if value is None:
        return desc_sig_keyword(nodes.Text("None"), **attributes)
    if isinstance(value, builtin_number_types):
        return desc_sig_literal_number(nodes.Text(repr(value)), **attributes)
    if is_builtin_string_type(value):
        if len(value) == 1:
            return desc_sig_literal_char(nodes.Text(repr(value)), **attributes)
        return desc_sig_literal_string(nodes.Text(repr(value)), **attributes)
    return desc_sig_element(nodes.Text(repr(value)), **attributes)


def desc_signature(
    signode: addnodes.desc_signature, signature: Signature, **attributes: AttributeValue
) -> addnodes.desc_signature:
    signode += desc_parameterlist(signature.parameters.values(), **attributes)
    if signature.return_annotation is not Signature.empty:
        signode += desc_sig_space()
        signode += desc_returns(signature.return_annotation, **attributes)
    return signode


def desc_returns(
    annotation: Any, **attributes: AttributeValue
) -> addnodes.desc_returns:
    return _with_children_and_attributes(
        addnodes.desc_returns(), desc_type(annotation, **attributes), **attributes
    )


def desc_parameterlist(
    parameters: Iterable[Parameter], **attributes: AttributeValue
) -> addnodes.desc_parameterlist:
    children: list[NodeLike] = []
    for parameter in parameters:
        children.append(desc_parameter(parameter))
    return _with_children_and_attributes(
        addnodes.desc_parameterlist(), *children, **attributes
    )


def desc_parameter(
    parameter: Parameter, **attributes: AttributeValue
) -> addnodes.desc_parameter:
    children: list[NodeLike] = []
    # Add the parameter name:
    children.append(desc_name(nodes.Text(parameter.name)))

    # Add the parameter type:
    if parameter.annotation is not Parameter.empty:
        children.append(desc_sig_operator(nodes.Text(":")))
        children.append(desc_sig_space())
        children.append(desc_type(parameter.annotation, **attributes))

    # Add the parameter default value:
    if parameter.default is not Parameter.empty:
        children.append(desc_sig_space())
        children.append(desc_sig_operator(nodes.Text("=")))
        children.append(desc_sig_space())
        children.append(desc_literal(parameter.annotation, **attributes))

    return _with_children_and_attributes(
        addnodes.desc_parameter(), *children, **attributes
    )


def desc_optional(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_optional:
    return _with_children_and_attributes(
        addnodes.desc_optional(), *children, **attributes
    )


def desc_sig_element(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_element:
    return _with_children_and_attributes(
        addnodes.desc_sig_element(), *children, **attributes
    )


def desc_sig_space(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_space:
    return _with_children_and_attributes(
        addnodes.desc_sig_space(), *children, **attributes
    )


def desc_sig_name(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_name:
    return _with_children_and_attributes(
        addnodes.desc_sig_name(), *children, **attributes
    )


def desc_sig_operator(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_operator:
    return _with_children_and_attributes(
        addnodes.desc_sig_operator(), *children, **attributes
    )


def desc_sig_punctuation(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_punctuation:
    return _with_children_and_attributes(
        addnodes.desc_sig_punctuation(), *children, **attributes
    )


def desc_sig_keyword(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_keyword:
    return _with_children_and_attributes(
        addnodes.desc_sig_keyword(), *children, **attributes
    )


def desc_sig_keyword_type(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_keyword_type:
    return _with_children_and_attributes(
        addnodes.desc_sig_keyword_type(), *children, **attributes
    )


def desc_sig_literal_number(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_literal_number:
    return _with_children_and_attributes(
        addnodes.desc_sig_literal_number(), *children, **attributes
    )


def desc_sig_literal_string(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_literal_string:
    return _with_children_and_attributes(
        addnodes.desc_sig_literal_string(), *children, **attributes
    )


def desc_sig_literal_char(
    *children: NodeLike, **attributes: AttributeValue
) -> addnodes.desc_sig_literal_char:
    return _with_children_and_attributes(
        addnodes.desc_sig_literal_char(), *children, **attributes
    )


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


def fragtable(*children: NodeLike, **attributes: AttributeValue) -> morenodes.fragtable:
    return _with_children_and_attributes(morenodes.fragtable(), *children, **attributes)


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
