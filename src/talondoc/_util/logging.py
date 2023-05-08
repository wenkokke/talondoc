import logging
import sys
from typing import cast


def getLogger(name: str) -> logging.LoggerAdapter:
    if "sphinx" in sys.modules:
        import sphinx.util.logging

        return cast(logging.LoggerAdapter, sphinx.util.logging.getLogger(name))
    else:
        return logging.LoggerAdapter(logger=logging.getLogger(name), extra={})
