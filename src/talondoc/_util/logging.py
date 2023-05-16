import logging
import sys
from typing import cast

if "sphinx" in sys.modules:
    from logging import DEBUG as DEBUG
    from logging import ERROR as ERROR
    from logging import INFO as INFO
    from logging import WARNING as WARNING
    from logging import basicConfig as basicConfig
else:
    from colorlog import DEBUG as DEBUG  # type: ignore[no-redef]
    from colorlog import ERROR as ERROR  # type: ignore[no-redef]
    from colorlog import INFO as INFO  # type: ignore[no-redef]
    from colorlog import WARNING as WARNING  # type: ignore[no-redef]
    from colorlog import basicConfig as basicConfig  # type: ignore[no-redef]


def getLogger(name: str) -> logging.LoggerAdapter:
    if "sphinx" in sys.modules:
        import sphinx.util.logging

        return cast(logging.LoggerAdapter, sphinx.util.logging.getLogger(name))
    else:
        logger = logging.getLogger(name)

        return logging.LoggerAdapter(logger=logger, extra={})
