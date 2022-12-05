import ast
import json
import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Union, cast

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Action:
    name: str
    description: str
    returns: str
    args: Dict[str, str]


def talon_repl_path() -> str:
    if platform.system() == "Windows":
        return os.path.expandvars(r"%APPDATA%\talon\.venv\Scripts\repl.bat")
    else:
        return os.path.expandvars(r"$HOME/.talon/.venv/bin/repl")


def send_to_repl(stdin: bytes) -> List[str]:
    talon_repl_proc = subprocess.Popen(
        [talon_repl_path()], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    assert talon_repl_proc.stdin is not None
    assert talon_repl_proc.stdout is not None
    talon_repl_proc.stdout.readline()
    talon_repl_proc.stdin.write(stdin)
    talon_repl_proc.stdin.flush()
    return talon_repl_proc.communicate()[0].decode().splitlines()


def cache_builtin(output_dir: Union[str, Path]):
    talon_version = send_to_repl(b"talon.app.version\n")[0].replace("'", "")
    lines = send_to_repl(b"actions.list()\n")

    action_dict = {}

    current_action: str = ""
    current_description: List[str] = []

    for item in lines:
        if item == "":
            continue
        elif item[0].isspace():
            # Item is description
            current_description.append(item.strip())
        else:
            # Add old action to grouped output
            if current_action != "" and current_description:
                # check if it is the initial action

                # Remove the function defs
                action_name = current_action.split("(")[0]

                # Get the prefix to filter out user prefix
                action_prefix = action_name.split(".")[0]

                # auto_format didn't have a prefix so this is a work around of that issue
                if len(current_action.split(".", 1)) == 2:
                    action_base = current_action.split(".", 1)[1]
                else:
                    action_base = current_action.split(".", 1)[0]
                if action_prefix != "user":
                    args = {}

                    function_def: ast.FunctionDef = cast(
                        ast.FunctionDef,
                        ast.parse(f"def {action_base}: ...").body[0],
                    )
                    if function_def.args.args:
                        for arg in function_def.args.args:
                            if isinstance(arg.annotation, ast.Attribute):
                                args[arg.arg] = ast.unparse(arg.annotation)
                            elif isinstance(arg.annotation, ast.Name):
                                args[arg.arg] = arg.annotation.id

                    if isinstance(function_def.returns, ast.Name):
                        returns = function_def.returns.id
                    else:
                        returns = ""

                    action_dict[action_name] = Action(
                        name=action_name,
                        description=" ".join(current_description),
                        args=args,
                        returns=returns,
                    )

            # Item is the start of a new action
            current_action = item.strip()
            current_description = []

    output_path: Path = Path(output_dir) / f"talon_actions_dict-{talon_version}.json"
    print(f"Writing built actions to {output_path}")
    with open(output_path, "w") as outfile:
        outfile.write(
            json.dumps(
                {key: asdict(value) for key, value in action_dict.items()}, indent=4
            )
        )


# extract_builtin()
