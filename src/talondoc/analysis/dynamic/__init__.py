import io
import json
import os
import platform
import subprocess
from contextlib import AbstractContextManager
from functools import cached_property
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

    @cached_property
    def actions_json(self) -> str:
        return "\n".join(
            self.eval_print(
                "import inspect",
                "import json",
                "",
                "action_dicts = []",
                "",
                "def _repr_obj(obj):",
                "  if obj in (inspect.Signature.empty, inspect.Parameter.empty):",
                "    return None",
                "  return repr(obj)",
                "",
                "def _repr_cls(cls):",
                "  if cls in (inspect.Signature.empty, inspect.Parameter.empty):",
                "    return None",
                "  if hasattr(cls,'__name__'):",
                "    return cls.__name__",
                "  return repr(cls)",
                "",
                "for action_impls in registry.actions.values():",
                "    for action_impl in action_impls:",
                "        signature = inspect.signature(action_impl.func)",
                "        parameter_type_hints = [",
                "           {",
                "             'name':parameter.name,",
                "             'kind':parameter.kind,",
                "             'default':_repr_obj(parameter.default),",
                "             'annotation':_repr_cls(parameter.annotation)",
                "           }",
                "           for parameter in signature.parameters.values()",
                "        ]",
                "        function_type_hints = {",
                "          'parameters':parameter_type_hints,",
                "          'return_annotation':_repr_cls(signature.return_annotation),",
                "        }",
                "        name = action_impl.path",
                "        description = action_impl.type_decl.desc",
                "        parent_name = action_impl.ctx.path",
                "        parent_type = type(action_impl.ctx).__name__",
                "        action_dicts.append({",
                "          'function_type_hints':function_type_hints,",
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

    @property
    def actions(self) -> Iterator[talon.Action]:
        for action_fields in json.loads(self.actions_json):
            yield talon.Action.load(action_fields)


def cache_builtin(output_dir: str) -> None:
    with TalonRepl() as repl:
        for action in repl.actions:
            print(action)
