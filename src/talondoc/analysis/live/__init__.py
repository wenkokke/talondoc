import importlib.resources
import io
import json
import os
import platform
import subprocess
import textwrap
from contextlib import AbstractContextManager
from functools import cached_property
from importlib.resources import Resource
from pathlib import Path
from types import TracebackType
from typing import Iterator, List, Optional, Sequence, Union

import packaging
from packaging.version import Version
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
            _LOGGER.debug(f"> {line}")

    def eval(self, *line: str, encoding: str = "utf-8") -> str:
        assert self._session and self._session.stdin and self._session_stdout
        __EOR__ = "END_OF_RESPONSE"
        is_EOR = lambda line: line == __EOR__
        print_EOR = f"print('{__EOR__}')"
        self._session.stdin.write(bytes("\n".join([*line, print_EOR]) + "\n", encoding))
        self._session.stdin.flush()
        return "\n".join(self._session_stdout.readuntil(is_EOR, timeout=1)).strip()

    def eval_file(self, file: str, *, encoding: str = "utf-8") -> str:
        return self.eval(
            f"with open('{file}', 'r', encoding='{encoding}') as f:",
            f"    exec(f.read())",
            f"",
        )

    def eval_resource(self, resource: Resource, *, encoding: str = "utf-8") -> str:
        file: str
        with importlib.resources.path(
            "talondoc.analysis.live.resources", resource
        ) as path:
            if path.exists():
                file = str(path.absolute())
            else:
                raise FileNotFoundError(path)
        return self.eval_file(file, encoding=encoding)

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
    def version(self) -> Version:
        parts = self.eval_resource("get_version.py").split("-", maxsplit=3)
        version = parts[0]
        if len(parts) >= 2:
            version += f"b{parts[1]}"
        if len(parts) >= 3:
            version += f"+{parts[2]}"
        return Version(version)

    @cached_property
    def actions(self) -> Sequence[talon.Action]:
        # Get the actions as JSON from Talon
        actions_json = self.eval_resource("get_actions.py")

        # Parse the JSON
        try:
            actions_fields = json.loads(actions_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()

        # Return the actions
        return tuple(map(talon.Action.load, actions_fields))


def cache_builtin(output_dir: str) -> None:
    with TalonRepl() as repl:
        print(repl.version)
        for action in repl.actions:
            print(action)
