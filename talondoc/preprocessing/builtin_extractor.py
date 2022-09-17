import ast
import json
import subprocess
from pathlib import Path


def send_to_repl(stdin: bytes) -> list[str]:
    talon_repl_path = Path.home() / "AppData\Roaming\\talon\.venv\Scripts\\repl.bat"
    proc = subprocess.Popen(
        [talon_repl_path],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(proc.stdout.readline())

    proc.stdin.write(stdin)
    proc.stdin.flush()
    lines: list[str] = proc.communicate()[0].decode().splitlines()

    return lines


talon_version = send_to_repl(b"talon.app.version\n")[0].replace("'", "")
lines = send_to_repl(b"actions.list()\n")


action_dict = {}
function_definitions = {}

current_action: str = ""
current_description: list[str] = []

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
            # action_base = current_action.replace(".", "\. ")
            if action_prefix != "user":
                action_dict[action_name.split("(")[0]] = " ".join(current_description)

                function_def = "def " + action_base + ": ..."
                function_definitions[action_name] = ast.parse(function_def)

        # Item is the start of a new action
        current_action = item.strip()
        current_description = []


# print()
# print(processed_output)
# print(function_definitions)
# print(talon_version)

output_path = Path.cwd() / ("talon_actions_dict" + talon_version + ".json")
with open(output_path, "w") as outfile:
    outfile.write(json.dumps(action_dict, indent=4))

# output_path = Path.cwd() / ("talon_actions_signatures" + talon_version + ".json")
# with open(output_path, "w") as outfile:
#     outfile.write(json.dumps(function_definitions, indent=4))
