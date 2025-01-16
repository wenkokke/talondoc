import json
import os
from collections.abc import Mapping

from .._util.logging import getLogger
from ..analysis.live import TalonRepl

_LOGGER = getLogger(__name__)


def cache_builtin(output_dir: str) -> None:
    with TalonRepl() as repl:
        version = str(repl.version)
        _LOGGER.info(f"Found Talon {version}")
        _LOGGER.info("Getting builtin declarations...")
        builtin = repl.builtin_registry.to_dict()
        if isinstance(builtin, Mapping):
            for cls, objs in builtin.items():
                if isinstance(objs, Mapping):
                    _LOGGER.info(f"Found {len(objs)} {cls.lower()}s")
        output_path = os.path.join(output_dir, "talon.json")
        with open(output_path, "w") as f:
            json.dump(builtin, f)
        _LOGGER.info(f"Wrote {output_path}")
