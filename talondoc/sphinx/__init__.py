from typing import Any
from sphinx.application import Sphinx
from .. import __version__
from .domains.talon import TalonDomain


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(TalonDomain)
    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
