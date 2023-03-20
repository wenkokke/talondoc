from collections.abc import Callable
from typing import Any, Optional, Sequence, Union
from typing_extensions import TypedDict
from pathlib import Path

from sphinx.application import Sphinx

from .. import __version__
from .domains import TalonDomain


TalonPackage = TypedDict('TalonPackage', {
  'path': Union[str, Path],
  'name': Optional[str],
  'include': Union[None, str, Sequence[str]],
  'exclude': Union[None, str, Sequence[str]],
  'trigger': Union[None, str, Sequence[str]],
})


TalonDocstringHook = Union[
  Callable[[str, str], Optional[str]],
  dict[str, dict[str, str]],
]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(TalonDomain)
    app.add_config_value(name="talon_docstring_hook", default=None, rebuild="env")
    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
