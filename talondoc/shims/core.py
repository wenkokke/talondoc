import collections.abc
import types
import typing


class ObjectShim:
    """
    A simple shim which responds to any method.
    """

    def __init__(self, **kwargs):
        pass

    def __getattr__(self, name: str) -> typing.Any:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self

    def __setattr__(self, name: str, value: typing.Any):
        object.__setattr__(self, name, value)

    def __getitem__(self, name: str) -> typing.Any:
        return self

    def __setitem__(self, name: str, value: typing.Any):
        pass

    def __enter__(self) -> typing.Any:
        return self

    def __exit__(self, *args):
        pass

    def __add__(self, other) -> typing.Any:
        return self

    def __sub__(self, other) -> typing.Any:
        return self

    def __mul__(self, other) -> typing.Any:
        return self

    def __pow__(self, other) -> typing.Any:
        return self

    def __mod__(self, other) -> typing.Any:
        return self

    def __floordiv__(self, other) -> typing.Any:
        return self

    def __truediv__(self, other) -> typing.Any:
        return self

    def __radd__(self, other) -> typing.Any:
        return self

    def __rsub__(self, other) -> typing.Any:
        return self

    def __rmul__(self, other) -> typing.Any:
        return self

    def __rmod__(self, other) -> typing.Any:
        return self

    def __rfloordiv__(self, other) -> typing.Any:
        return self

    def __rtruediv__(self, other) -> typing.Any:
        return self

    def __abs__(self) -> typing.Any:
        return self

    def __neg__(self) -> typing.Any:
        return self

    def __trunc__(self) -> typing.Any:
        return self

    def __floor__(self) -> typing.Any:
        return self

    def __ceil__(self) -> typing.Any:
        return self

    def __and__(self, other) -> typing.Any:
        return self

    def __rand__(self, other) -> typing.Any:
        return self

    def __or__(self, other) -> typing.Any:
        return self

    def __ror__(self, other) -> typing.Any:
        return self

    def __xor__(self, other) -> typing.Any:
        return self

    def __rxor__(self, other) -> typing.Any:
        return self

    def __invert__(self) -> typing.Any:
        return self

    def __lshift__(self, other) -> typing.Any:
        return self

    def __rlshift__(self, other) -> typing.Any:
        return self

    def __rshift__(self, other) -> typing.Any:
        return self

    def __rrshift__(self, other) -> typing.Any:
        return self

    def __call__(self, *args, **kwargs) -> typing.Any:
        return self

    def __iter__(self) -> collections.abc.Iterator:
        return ().__iter__()


class ModuleShim(types.ModuleType, ObjectShim):
    """
    A module shim which defines typing.any value.
    """

    def __init__(self, fullname: str):
        super().__init__(fullname)
