from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeGuard, cast

from sphinx.application import BuildEnvironment, Sphinx

from .._util.logging import getLogger
from .._version import __version__
from ..analysis.registry import NoActiveFile, NoActivePackage, NoActiveRegistry
from ..analysis.static import analyse_package
from ._util.addnodes.fragtable import (
    depart_fragtable,
    depart_fragtable_html,
    fragtable,
    visit_fragtable,
    visit_fragtable_html,
)
from .domains import TalonDomain
from .typing import TalonPackage

_LOGGER = getLogger(__name__)


def _is_talon_package(talon_package: Any) -> TypeGuard[TalonPackage]:
    try:
        if not isinstance(talon_package, dict):
            raise TypeError(
                "talon_package must be a dictionary"
                f"and is {type(talon_package).__name__}"
            )

        path = talon_package.get("path", None)
        if not isinstance(path, str | Path):
            raise TypeError("talon_package path must be a string or a path")

        name = talon_package.get("name", None)
        if not isinstance(name, str):
            raise TypeError(
                f"talon_package.name must be a string and is {type(name).__name__}"
            )

        include = talon_package.get("include", None)
        if not (
            include is None
            or isinstance(include, str | Path)
            or (
                isinstance(include, Sequence)
                and all(isinstance(path, str | Path) for path in include)
            )
        ):
            raise TypeError(
                "talon_package.include must be none, a string, or a sequence of strings"
                f"and is {type(include).__name__}"
            )

        exclude = talon_package.get("exclude", None)
        if not (
            exclude is None
            or isinstance(exclude, str | Path)
            or (
                isinstance(exclude, Sequence)
                and all(isinstance(path, str | Path) for path in exclude)
            )
        ):
            raise TypeError(
                "talon_package.exclude must be none,a string, or a sequence of strings"
                f"and is {type(exclude).__name__}"
            )

        trigger = talon_package.get("trigger", None)
        if not (
            trigger is None
            or isinstance(trigger, str)
            or (
                isinstance(trigger, Sequence)
                and all(isinstance(event, str) for event in trigger)
            )
        ):
            raise TypeError(
                "talon_package.trigger must be none, a string, or a sequence of strings"
                f"and is {type(trigger).__name__}"
            )
        return True
    except TypeError:
        return False


def _canonicalize_talon_package(talon_package: Any) -> TalonPackage | None:
    match talon_package:
        case str():
            return {"path": talon_package}
        case dict() if _is_talon_package(talon_package):
            return talon_package
        case None:
            return None
        case _:
            raise TypeError(type(talon_package))


def _canonicalize_talon_packages(talon_packages: Any) -> Sequence[TalonPackage]:
    if talon_packages is None:
        return ()
    try:
        talon_package = _canonicalize_talon_package(talon_packages)
        return (talon_package,) if talon_package else ()
    except TypeError:
        pass
    if isinstance(talon_packages, Sequence):
        return tuple(
            filter(
                None,
                (
                    _canonicalize_talon_package(talon_package)
                    for talon_package in talon_packages
                ),
            )
        )
    raise TypeError(type(talon_packages))


def _canonicalize_vararg(vararg: None | str | Sequence[str]) -> Sequence[str]:
    match vararg:
        case str():
            return (vararg,)
        case Sequence():
            return tuple(vararg)
        case None:
            return ()
        case _:
            raise TypeError(type(vararg))


def _talon_packages(env: BuildEnvironment) -> Sequence[TalonPackage]:
    buffer = []

    # Load via the talon_package option
    talon_package = _canonicalize_talon_package(env.config["talon_package"])
    if talon_package:
        buffer.append(talon_package)

    # Load via the talon_packages option
    talon_packages = _canonicalize_talon_packages(env.config["talon_packages"])
    if talon_packages:
        buffer.extend(talon_packages)

    return buffer


def _talondoc_load_package(app: Sphinx, env: BuildEnvironment, *args: Any) -> None:
    try:
        talon_domain = cast(TalonDomain, env.get_domain("talon"))
        talon_packages = _talon_packages(env)
        continue_on_error = bool(env.config["talon_continue_on_error"])
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
                    continue_on_error=continue_on_error,
                )
            except NoActiveRegistry as e:
                _LOGGER.exception(e)
            except NoActivePackage as e:
                _LOGGER.exception(e)
            except NoActiveFile as e:
                _LOGGER.exception(e)
    except Exception as e:
        _LOGGER.exception(e)


def setup(app: Sphinx) -> dict[str, Any]:
    # Add fragmenting table nodes
    app.add_node(
        fragtable,
        html=(visit_fragtable_html, depart_fragtable_html),
        latex=(visit_fragtable, depart_fragtable),
        text=(visit_fragtable, depart_fragtable),
    )

    # Add the Talon domain
    app.add_domain(TalonDomain)

    # Add the TalonDoc configuration options
    app.add_config_value(
        name="talon_docstring_hook",
        default=None,
        rebuild="env",
        types=[
            Callable,  # _TalonDocstringHook_Callable
            dict,  # _TalonDocstringHook_Dict
        ],
    )

    app.add_config_value(
        name="talon_package",
        default=None,
        rebuild="env",
        types=[
            dict,  # TalonPackage
            str,
        ],
    )

    app.add_config_value(
        name="talon_packages",
        default=None,
        rebuild="env",
        types=[
            list,  # list[TalonPackage]
            tuple,  # Tuple[TalonPackage]
        ],
    )
    app.add_config_value(
        name="talon_continue_on_error",
        default=None,
        rebuild="env",
        types=[bool],
    )

    # Add the hook to load any Talon packages
    app.connect("env-before-read-docs", _talondoc_load_package)

    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
