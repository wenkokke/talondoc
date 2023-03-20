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
      types=[
        _TalonDocstringHook_Callable,
        _TalonDocstringHook_Dict,
      ]
    )
    
    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
