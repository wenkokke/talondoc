import logging
import sys


def getLogger(name: str) -> logging.LoggerAdapter:
    if "sphinx" in sys.modules:
        import sphinx.util.logging

        return sphinx.util.logging.getLogger(name)  # type: ignore
    else:
        return logging.LoggerAdapter(logger=logging.getLogger(name), extra={})
