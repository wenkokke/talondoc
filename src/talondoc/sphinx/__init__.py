from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Optional, Union, cast

from sphinx.application import BuildEnvironment, Sphinx
from typing_extensions import TypeGuard

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


def _canonicalize_talon_package(talon_package: Any) -> Optional[TalonPackage]:
    if talon_package is None:
        return None
    if type(talon_package) == str:
        return {"path": talon_package}
    if _is_talon_package(talon_package):
        return talon_package
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


def _canonicalize_vararg(vararg: Union[None, str, Sequence[str]]) -> Sequence[str]:
    if vararg is None:
        return ()
    if type(vararg) == str:
        return (vararg,)
    if isinstance(vararg, Sequence):
        return tuple(vararg)
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
