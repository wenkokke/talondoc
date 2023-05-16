import dataclasses
import typing

import packaging.version
import tree_sitter_talon

##############################################################################
# Pickle Compatibility
##############################################################################

COMPAT: bool

if packaging.version.Version(
    tree_sitter_talon.__version__
) <= packaging.version.Version("1007.3.2.0"):
    COMPAT = True

    def _fields(obj) -> typing.Tuple[typing.Any, ...]:
        assert dataclasses.is_dataclass(obj)
        return tuple(getattr(obj, field.name) for field in dataclasses.fields(obj))

    def _make_TalonUnaryOperator(*args) -> tree_sitter_talon.TalonUnaryOperator:
        return tree_sitter_talon.TalonUnaryOperator(*args)

    setattr(
        tree_sitter_talon.TalonUnaryOperator,
        "__reduce__",
        lambda self: (_make_TalonUnaryOperator, _fields(self)),
    )

else:
    COMPAT = False
