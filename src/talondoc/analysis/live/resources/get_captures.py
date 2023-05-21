import talon  # pyright: ignore[reportMissingImports]


def _get_captures() -> None:
    import base64
    import inspect
    import json
    import pickle
    import typing

    capture_dicts = []

    def asdict_pickle(value: typing.Any) -> typing.Any:
        if isinstance(value, str):
            return value
        else:
            return {
                "pickle": base64.b64encode(pickle.dumps(value)).decode(encoding="utf-8")
            }

    def asdict_class(cls: type) -> typing.Optional[str]:
        if cls in (inspect.Signature.empty, inspect.Parameter.empty):
            return None
        if hasattr(cls, "__name__"):
            return cls.__name__
        return repr(cls)

    def asdict_parameter(par: inspect.Parameter) -> typing.Dict[str, typing.Any]:
        return {
            "name": par.name,
            "kind": par.kind,
            "default": asdict_pickle(par.default),
            "annotation": asdict_class(par.annotation),
        }

    def asdict_signature(sig: inspect.Signature) -> typing.Dict[str, typing.Any]:
        return {
            "parameters": [asdict_parameter(par) for par in sig.parameters.values()],
            "return_annotation": asdict_class(sig.return_annotation),
        }

    for capture_impls in talon.registry.captures.values():
        for capture_impl in capture_impls:
            name = capture_impl.path
            description = capture_impl.func.__doc__
            parent_name = capture_impl.ctx.path
            parent_type = type(capture_impl.ctx).__name__
            capture_dicts.append(
                {
                    "rule": capture_impl.rule.rule,
                    "function_signature": asdict_signature(
                        inspect.signature(capture_impl.func)
                    ),
                    "name": name,
                    "description": description,
                    "location": "builtin",
                    "parent_type": parent_type,
                    "parent_name": parent_name,
                }
            )
    print(json.dumps(capture_dicts))


_get_captures()
del _get_captures
