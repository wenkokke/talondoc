import talon  # pyright: ignore[reportMissingImports]


def _get_actions() -> None:
    import inspect
    import json
    import typing

    action_dicts = []

    def repr_obj(obj: object) -> typing.Optional[str]:
        if obj in (inspect.Signature.empty, inspect.Parameter.empty):
            return None
        return repr(obj)

    def repr_cls(cls: type) -> typing.Optional[str]:
        if cls in (inspect.Signature.empty, inspect.Parameter.empty):
            return None
        if hasattr(cls, "__name__"):
            return cls.__name__
        return repr(cls)

    for action_impls in talon.registry.actions.values():
        for action_impl in action_impls:
            signature = inspect.signature(action_impl.func)
            parameter_type_hints = [
                {
                    "name": parameter.name,
                    "kind": parameter.kind,
                    "default": repr_obj(parameter.default),
                    "annotation": repr_cls(parameter.annotation),
                }
                for parameter in signature.parameters.values()
            ]
            function_type_hints = {
                "parameters": parameter_type_hints,
                "return_annotation": repr_cls(signature.return_annotation),
            }
            name = action_impl.path
            description = action_impl.type_decl.desc
            parent_name = action_impl.ctx.path
            parent_type = type(action_impl.ctx).__name__
            action_dicts.append(
                {
                    "function_type_hints": function_type_hints,
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
