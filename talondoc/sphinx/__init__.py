from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Sequence, Union, cast

from sphinx.application import Sphinx
from typing_extensions import (
    NotRequired,
    Required,
    TypeAlias,
    TypedDict,
    TypeGuard,
    TypeVar,
)

from talondoc.registry import NoActiveFile, NoActivePackage, NoActiveRegistry

from .. import __version__
from ..analyze import analyse_package
from ..util.logging import getLogger
from .domains import TalonDomain

_LOGGER = getLogger(__name__)

TalonEvent = str

TalonPackage = TypedDict(
    "TalonPackage",
    {
        "path": Required[str],
        "name": NotRequired[str],
        "include": NotRequired[Union[str, Sequence[str]]],
        "exclude": NotRequired[Union[str, Sequence[str]]],
        "trigger": NotRequired[Union[TalonEvent, Sequence[TalonEvent]]],
    },
)


def _is_talon_package(talon_package: Any) -> TypeGuard[TalonPackage]:
    try:
        assert isinstance(talon_package, dict)
        path = talon_package.get("path", None)
        assert isinstance(path, (str, Path))
        name = talon_package.get("name", None)
        assert isinstance(name, (str,))
        include = talon_package.get("include", None)
        assert (
            include is None
            or isinstance(include, (str, Path))
            or (
                isinstance(include, Sequence)
                and all(isinstance(path, (str, Path)) for path in include)
            )
        )
        exclude = talon_package.get("exclude", None)
        assert (
            exclude is None
            or isinstance(exclude, (str, Path))
            or (
                isinstance(exclude, Sequence)
                and all(isinstance(path, (str, Path)) for path in exclude)
            )
        )
        trigger = talon_package.get("trigger", None)
        assert (
            trigger is None
            or isinstance(trigger, str)
            or (
                isinstance(trigger, Sequence)
                and all(isinstance(event, (str,)) for event in trigger)
            )
        )
        return True
    except AssertionError:
        return False


def _canonicalize_talon_package(talon_package: Any) -> TalonPackage:
    if type(talon_package) == str:
        return {"path": talon_package}
    if _is_talon_package(talon_package):
        return talon_package
    raise TypeError(type(talon_package))


def _canonicalize_talon_packages(talon_packages: Any) -> Sequence[TalonPackage]:
    try:
        return [_canonicalize_talon_package(talon_packages)]
    except TypeError:
        pass
    if isinstance(talon_packages, Sequence):
        return [
            _canonicalize_talon_package(talon_package)
            for talon_package in talon_packages
        ]
    raise TypeError(type(talon_packages))


def _canonicalize_vararg(vararg: Union[None, str, Sequence[str]]) -> tuple[str, ...]:
    if vararg is None:
        return ()
    if type(vararg) == str:
        return (vararg,)
    if isinstance(vararg, Sequence):
        return tuple(vararg)
    raise TypeError(type(vararg))


def _talondoc_load_package(app, env, *args):
    talon_domain = cast(TalonDomain, env.get_domain("talon"))
    talon_packages = _canonicalize_talon_packages(env.config["talon_packages"])
    srcdir = Path(env.srcdir)
    for talon_package in talon_packages:
        package_dir = srcdir / talon_package["path"]

        # Analyse the referenced Talon package:
        try:
            analyse_package(
                registry=talon_domain.registry,
                package_dir=package_dir,
                package_name=talon_package.get("name", "user"),
                include=_canonicalize_vararg(talon_package.get("include")),
                exclude=_canonicalize_vararg(talon_package.get("exclude")),
                trigger=_canonicalize_vararg(talon_package.get("trigger")),
            )
        except NoActiveRegistry as e:
            _LOGGER.exception(e)
        except NoActivePackage as e:
            _LOGGER.exception(e)
        except NoActiveFile as e:
            _LOGGER.exception(e)


_TalonDocstringHook_Callable: TypeAlias = Callable[[str, str], Optional[str]]
_TalonDocstringHook_Dict: TypeAlias = dict[str, dict[str, str]]


TalonDocstringHook: TypeAlias = Union[
    _TalonDocstringHook_Callable,
    _TalonDocstringHook_Dict,
]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(TalonDomain)

    app.add_config_value(
        name="talon_docstring_hook",
        default=None,
        rebuild="env",
        # types=[
        #     Callable[[str, str], Optional[str]],
        #     dict[str, dict[str, str]],
        # ],
    )

    app.add_config_value(
        name="talon_packages",
        default=None,
        rebuild="env",
        # types=[
        #     str,
        #     TalonPackage,
        #     Sequence[str],
        #     Sequence[TalonPackage],
        # ],
    )

    app.connect("env-before-read-docs", _talondoc_load_package)

    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
