import io
import os
import platform
import subprocess
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Iterator, Optional, Union

from typing_extensions import Self

from ..._util.io import NonBlockingTextIOWrapper
from ..._util.logging import getLogger
from ..registry import entries as talon

_LOGGER = getLogger(__name__)


class TalonRepl(AbstractContextManager):
    _session: Optional[subprocess.Popen[bytes]]
    _session_stdout: Optional[NonBlockingTextIOWrapper]
    _session_stderr: Optional[NonBlockingTextIOWrapper]

    @property
    def executable_path(self) -> str:
        if platform.system() == "Windows":
            return os.path.expandvars("%APPDATA%\\talon\\.venv\\Scripts\\repl.bat")
        else:
            return os.path.expandvars("$HOME/.talon/.venv/bin/repl")

    def __enter__(self) -> Self:
        self.open()
        return self

    def open(self) -> None:
        self._session = subprocess.Popen(
            [],
            executable=self.executable_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Create stdout wrapper:
        assert self._session.stdout is not None
        self._session_stdout = NonBlockingTextIOWrapper(
            io.TextIOWrapper(self._session.stdout, encoding="utf-8")
        )
        # Create stderr wrapper:
        assert self._session.stderr is not None
        self._session_stderr = NonBlockingTextIOWrapper(
            io.TextIOWrapper(self._session.stderr, encoding="utf-8")
        )
        # Read at least one line from stdout:
        for line in self._session_stdout.readlines(minlines=1):
            print(line)

    def eval(self, *line: str) -> None:
        assert self._session and self._session.stdin
        self._session.stdin.write(bytes("\n".join(line) + "\n", "utf-8"))
        self._session.stdin.flush()

    def eval_print(self, *line: str) -> Iterator[str]:
        assert self._session_stdout
        _END_OF_RESPONSE = "END_OF_RESPONSE"
        self.eval(*line, f"print('{_END_OF_RESPONSE}')")
        yield from self._session_stdout.readwhile(
            lambda line: line != _END_OF_RESPONSE, timeout=1
        )

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._session:
            self.eval("exit()")
            self._session.wait()


def cache_builtin(output_dir: Union[str, Path]):
    with TalonRepl() as repl:
        print("BEGIN")
        print(
            "\n".join(
                repl.eval_print(
                    "import inspect",
                    "import json",
                    "",
                    "action_dicts = []",
                    "",
                    "for action_impls in registry.actions.values():",
                    "    for action_impl in action_impls:",
                    "        name = action_impl.path",
                    "        description = action_impl.type_decl.desc",
                    "        parent_name = action_impl.ctx.path",
                    "        parent_type = type(action_impl.ctx).__name__",
                    "        action_dicts.append({",
                    "          'name':name,",
                    "          'description':description,",
                    "          'location':'builtin',",
                    "          'parent_type':parent_type,",
                    "          'parent_name':parent_name,",
                    "        })",
                    "",
                    "print(json.dumps(action_dicts))",
                )
            )
        )
        print("END")


# @dataclass_json
# @dataclass
# class BuiltinActionEntry:
#     name: str
#     description: str
#     returns: str
#     args: typing.Dict[str, str]


# def talon_repl_path() -> str:
#     if platform.system() == "Windows":
#         return os.path.expandvars(r"%APPDATA%\talon\.venv\Scripts\repl.bat")
#     else:
#         return os.path.expandvars(r"$HOME/.talon/.venv/bin/repl")


# def send_to_repl(stdin: bytes) -> typing.List[str]:
#     talon_repl_proc = subprocess.Popen(
#         [talon_repl_path()], stdin=subprocess.PIPE, stdout=subprocess.PIPE
#     )
#     assert talon_repl_proc.stdin is not None
#     assert talon_repl_proc.stdout is not None
#     talon_repl_proc.stdout.readline()
#     talon_repl_proc.stdin.write(stdin)
#     talon_repl_proc.stdin.flush()
#     return talon_repl_proc.communicate()[0].decode().splitlines()


# def cache_builtin(output_dir: typing.Union[str, Path]):
#     talon_version = send_to_repl(b"talon.app.version\n")[0].replace("'", "")
#     lines = send_to_repl(b"actions.list()\n")

#     action_dict = {}

#     current_action: str = ""
#     current_description: typing.List[str] = []

#     for item in lines:
#         if item == "":
#             continue
#         elif item[0].isspace():
#             # Item is description
#             current_description.append(item.strip())
#         else:
#             # Add old action to grouped output
#             if current_action != "" and current_description:
#                 # check if it is the initial action

#                 # Remove the function defs
#                 action_name = current_action.split("(")[0]

#                 # Get the prefix to filter out user prefix
#                 action_prefix = action_name.split(".")[0]

#                 # auto_format didn't have a prefix so this is a work around of that issue
#                 if len(current_action.split(".", 1)) == 2:
#                     action_base = current_action.split(".", 1)[1]
#                 else:
#                     action_base = current_action.split(".", 1)[0]
#                 if action_prefix != "user":
#                     args = {}

#                     function_def: ast.FunctionDef = typing.cast(
#                         ast.FunctionDef,
#                         ast.parse(f"def {action_base}: ...").body[0],
#                     )
#                     if function_def.args.args:
#                         for arg in function_def.args.args:
#                             if isinstance(arg.annotation, ast.Attribute):
#                                 args[arg.arg] = ast.unparse(arg.annotation)
#                             elif isinstance(arg.annotation, ast.Name):
#                                 args[arg.arg] = arg.annotation.id

#                     if isinstance(function_def.returns, ast.Name):
#                         returns = function_def.returns.id
#                     else:
#                         returns = ""

#                     action_dict[action_name] = BuiltinActionEntry(
#                         name=action_name,
#                         description=" ".join(current_description),
#                         args=args,
#                         returns=returns,
#                     )

#             # Item is the start of a new action
#             current_action = item.strip()
#             current_description = []

#     output_path: Path = Path(output_dir) / f"talon_actions_dict-{talon_version}.json"
#     print(f"Writing built actions to {output_path}")
#     with open(output_path, "w") as outfile:
#         outfile.write(
#             json.dumps(
#                 {key: asdict(value) for key, value in action_dict.items()},
#                 indent=4,
#             )
#         )
