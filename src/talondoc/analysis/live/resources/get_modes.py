import talon  # pyright: ignore[reportMissingImports]


def _get_modes() -> None:
    import json

    mode_dicts = []

    for mod in talon.registry.modules.values():
        for mode in mod._modes.values():
            mode_dicts.append(
                {
                    "name": mode.path,
                    "description": mode.desc,
                    "parent_name": mod.path,
                }
            )
    print(json.dumps(mode_dicts))


_get_modes()
del _get_modes
