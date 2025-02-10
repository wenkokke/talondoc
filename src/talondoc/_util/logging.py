import logging
import sys
from logging import DEBUG as DEBUG
from logging import ERROR as ERROR
from logging import INFO as INFO
from logging import WARNING as WARNING
from logging import LogRecord
from typing import cast

if "sphinx" in sys.modules:
    from logging import basicConfig as basicConfig  # type: ignore[no-redef]
else:
    from colorlog import basicConfig as basicConfig  # type: ignore[no-redef]

if "sphinx" not in sys.modules:
    import colorlog

    class PrettyColoredFormatter(colorlog.ColoredFormatter):  # type: ignore[misc]
        def format(self, record: LogRecord) -> str:
            if record.levelno == INFO:
                return record.getMessage()
            return super().format(record)  # type: ignore[no-any-return]

    _FORMATTER = PrettyColoredFormatter(
        fmt="%(log_color)s%(levelname)s: %(message)s",
        log_colors={"ERROR": "red", "WARNING": "red"},
    )

    _HANDLER = logging.StreamHandler()
    _HANDLER.setFormatter(_FORMATTER)

if "sphinx" in sys.modules:

    def getLogger(name: str) -> logging.Logger:  # type: ignore[no-redef]
        import sphinx.util.logging

        return cast(logging.Logger, sphinx.util.logging.getLogger(name))

else:

    def getLogger(name: str) -> logging.Logger:  # type: ignore[no-redef]
        logger = logging.getLogger(__name__)
        logger.propagate = False
        logger.addHandler(_HANDLER)
        return logger
