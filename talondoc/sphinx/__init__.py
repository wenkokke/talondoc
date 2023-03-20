from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from sphinx.application import Sphinx
from typing_extensions import TypeAlias, TypedDict

from .. import __version__
from .domains import TalonDomain

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


TalonDocstringHook: TypeAlias = Union[
    Callable[[str, str], Optional[str]],
    dict[str, dict[str, str]],
]

_TalonDocstringHook_Callable: TypeAlias = Callable[[str, str], Optional[str]]

print(_TalonDocstringHook_Callable.__name__)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(TalonDomain)

    app.add_config_value(
        name="talon_docstring_hook",
        default=None,
        rebuild="env",
        types=[
            Callable[[str, str], Optional[str]],
            dict[str, dict[str, str]],
        ],
    )

    app.add_config_value(
        name="talon_packages",
        default=None,
        rebuild="env",
        types=[
            str,
            TalonPackage,
            Sequence[str],
            Sequence[TalonPackage],
        ],
    )

    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
