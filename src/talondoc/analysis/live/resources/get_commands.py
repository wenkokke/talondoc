import talon  # pyright: ignore[reportMissingImports]


def _get_commands() -> None:
    import json

    command_dicts = []

    for command_name, command_impls in talon.registry.commands.items():
        for command_impl in command_impls:
            rule = command_impl.rule.rule
            script = command_impl.script.code
            name = command_name
            path = command_impl.script.filename
            start_line = command_impl.script.start_line
            end_line = start_line + len(command_impl.script.lines) - 1
            location = {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
            }
            parent_name = command_impl.ctx.path
            parent_type = type(command_impl.ctx).__name__
            command_dicts.append(
                {
                    "rule": rule,
                    "script": script,
                    "name": name,
                    "location": location,
                    "parent_type": parent_type,
                    "parent_name": parent_name,
                }
            )
    print(json.dumps(command_dicts))


_get_commands()
del _get_commands
