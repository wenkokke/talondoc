import json

from ..analysis.live import TalonRepl


def cache_builtin(output_dir: str) -> None:
    with TalonRepl() as repl:
        print(
            json.dumps(
                {
                    "version": str(repl.version),
                    "registry": repl.builtin_registry.to_dict(),
                }
            )
        )
