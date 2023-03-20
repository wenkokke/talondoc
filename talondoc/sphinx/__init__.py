from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Sequence, Union, cast

from sphinx.application import Sphinx
from typing_extensions import TypeAlias, TypedDict

from ..analyze import analyse_package
from .. import __version__
from ..util.logging import getLogger
from .domains import TalonDomain

_LOGGER = getLogger(__name__)

TalonPackage = TypedDict(
    "TalonPackage",
    {
        "path": Union[str, Path],
        "name": Optional[str],
        "include": Union[None, str, Sequence[str]],
        "exclude": Union[None, str, Sequence[str]],
        "trigger": Union[None, str, Sequence[str]],
    },
)


def _convert_talon_packages(talon_packages: Any) -> Sequence[TalonPackage]:
    if type(talon_packages) == str:
        return [{"path": talon_packages}]
    if isinstance(talon_packages, TalonPackage):
        return [talon_packages]
    if isinstance(talon_packages, Sequence):
        buffer = []
        for talon_package in talon_packages:
            buffer.extend(convert_talon_packages(talon_package))
        return buffer
    raise TypeError(type(talon_packages))


def _convert_tuple(value: Union[None, str, Sequence[str]]) -> tuple[str, ...]:
    if value is None:
        return ()
    if type(value) == str:
        return (value,)
    if isinstance(value, Sequence):
        return tuple(value)
    raise TypeError(type(value))


def env_get_outdated_handler(app, env, added, changed, removed):
    talon_domain = cast(TalonDomain, env.get_domain("talon"))
    talon_packages = _convert_talon_packages(env.config["talon_packages"])
    srcdir = Path(env.srcdir)
    for talon_package in talon_packages:
        package_dir = srcdir / talon_package["path"]

        # Analyse the referenced Talon package:
        try:
            analyse_package(
                registry=self.talon.registry,
                package_dir=package_dir,
                package_name=talon_package.get("name", "user"),
                include=_convert_tuple(talon_package.get("include")),
                exclude=_convert_tuple(talon_package.get("exclude")),
                trigger=_convert_tuple(talon_package.get("trigger")),
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

    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
