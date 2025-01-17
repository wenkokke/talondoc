import talon  # pyright: ignore[reportMissingImports]


def _get_settings() -> None:
    import base64
    import json
    import pickle
    import typing

    def asdict_pickle(value: typing.Any) -> typing.Any:
        if isinstance(value, str):
            return value
        else:
            return {
                "pickle": base64.b64encode(pickle.dumps(value)).decode(encoding="utf-8")
            }

    def asdict_class(cls: type) -> str | None:
        if hasattr(cls, "__name__"):
            return cls.__name__
        return repr(cls)

    setting_dicts = []

    for mod in talon.registry.modules.values():
        for setting in mod._settings.values():
            setting_dicts.append(
                {
                    "value": asdict_pickle(setting.default),
                    "value_type_hint": asdict_class(setting.type),
                    "name": setting.path,
                    "description": setting.desc,
                    "parent_name": mod.path,
                    "parent_type": "Module",
                }
            )

    for ctx in talon.registry.contexts.values():
        for setting_name, setting_value in ctx._settings.items():
            setting_dicts.append(
                {
                    "value": asdict_pickle(setting_value),
                    "name": setting_name,
                    "parent_name": ctx.path,
                    "parent_type": "Context",
                }
            )

    print(json.dumps(setting_dicts))


_get_settings()
del _get_settings
