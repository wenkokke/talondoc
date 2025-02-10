import talon  # pyright: ignore[reportMissingImports]


def _get_lists() -> None:
    import base64
    import json
    import pickle
    import typing

    def asdict_pickle(value: typing.Any) -> typing.Any:
        if isinstance(value, str):
            return value
        return {
            "pickle": base64.b64encode(pickle.dumps(value)).decode(encoding="utf-8")
        }

    def asdict_list_value(value: typing.Mapping[typing.Any, typing.Any]) -> typing.Any:
        return {key: asdict_pickle(val) for key, val in value.items()}

    list_dicts = []

    for mod in talon.registry.modules.values():
        for list in mod._lists.values():
            list_dicts.append(
                {
                    "name": list.path,
                    "description": list.desc,
                    "parent_name": mod.path,
                    "parent_type": "Module",
                }
            )

    for ctx in talon.registry.contexts.values():
        for list_name, list_value in ctx._lists.items():
            list_dicts.append(
                {
                    "value": asdict_list_value(list_value),
                    "name": list_name,
                    "parent_name": ctx.path,
                    "parent_type": "Context",
                }
            )

    print(json.dumps(list_dicts))


_get_lists()
del _get_lists
