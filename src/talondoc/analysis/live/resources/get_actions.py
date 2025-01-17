import talon  # pyright: ignore[reportMissingImports]


def _get_actions() -> None:
    import base64
    import inspect
    import json
    import pickle
    import typing

    action_dicts = []

    def asdict_pickle(value: typing.Any) -> typing.Any:
        if isinstance(value, str):
            return value
        else:
            return {
                "pickle": base64.b64encode(pickle.dumps(value)).decode(encoding="utf-8")
            }

    def asdict_class(cls: type) -> str | None:
        if cls in (inspect.Signature.empty, inspect.Parameter.empty):
            return None
        if hasattr(cls, "__name__"):
            return cls.__name__
        return repr(cls)

    def asdict_parameter(par: inspect.Parameter) -> dict[str, typing.Any]:
        return {
            "name": par.name,
            "kind": par.kind,
            "default": asdict_pickle(par.default),
            "annotation": asdict_class(par.annotation),
        }

    def asdict_signature(sig: inspect.Signature) -> dict[str, typing.Any]:
        return {
            "parameters": [asdict_parameter(par) for par in sig.parameters.values()],
            "return_annotation": asdict_class(sig.return_annotation),
        }

    for action_impls in talon.registry.actions.values():
        for action_impl in action_impls:
            name = action_impl.path
            description = action_impl.type_decl.desc
            parent_name = action_impl.ctx.path
            parent_type = type(action_impl.ctx).__name__
            action_dicts.append(
                {
                    "function_signature": asdict_signature(
                        inspect.signature(action_impl.func)
                    ),
                    "name": name,
                    "description": description,
                    "location": "builtin",
                    "parent_type": parent_type,
                    "parent_name": parent_name,
                }
            )
    print(json.dumps(action_dicts))


_get_actions()
del _get_actions
