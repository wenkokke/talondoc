from typing import Any

from sphinx.application import Sphinx

from .. import __version__
from .domains import TalonDomain


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(TalonDomain)
    app.add_config_value(name="custom_docstring_hook", default=None, rebuild="env")
    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
