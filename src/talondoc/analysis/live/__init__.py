import importlib.resources
import io
import json
import os
import platform
import subprocess
from contextlib import AbstractContextManager
from functools import cached_property
from importlib.resources import Resource
from types import TracebackType
from typing import Optional, Sequence

from packaging.version import Version
from typing_extensions import Self

from ..._util.io import NonBlockingTextIOWrapper
from ..._util.logging import getLogger
from ..registry import Registry
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
        pep440_version = parts[0]
        if len(parts) >= 2:
            pep440_version += f"b{parts[1]}"
        if len(parts) >= 3:
            pep440_version += f"+{parts[2]}"
        return Version(pep440_version)

    @cached_property
    def actions(self) -> Sequence[talon.Action]:
        actions_json = self.eval_resource("get_actions.py")
        try:
            actions_fields = json.loads(actions_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.Action.from_dict, actions_fields))

    @property
    def builtin_actions(self) -> Sequence[talon.Action]:
        return tuple(filter(lambda action: action.builtin, self.actions))

    @cached_property
    def captures(self) -> Sequence[talon.Capture]:
        captures_json = self.eval_resource("get_captures.py")
        try:
            captures_fields = json.loads(captures_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.Capture.from_dict, captures_fields))

    @property
    def builtin_captures(self) -> Sequence[talon.Capture]:
        return tuple(filter(lambda capture: capture.builtin, self.captures))

    @cached_property
    def commands(self) -> Sequence[talon.Command]:
        commands_json = self.eval_resource("get_commands.py")
        try:
            commands_fields = json.loads(commands_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.Command.from_dict, commands_fields))

    @cached_property
    def lists(self) -> Sequence[talon.List]:
        lists_json = self.eval_resource("get_lists.py")
        try:
            lists_fields = json.loads(lists_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.List.from_dict, lists_fields))

    @property
    def builtin_lists(self) -> Sequence[talon.List]:
        return tuple(filter(lambda list: list.builtin, self.lists))

    @cached_property
    def settings(self) -> Sequence[talon.Setting]:
        settings_json = self.eval_resource("get_settings.py")
        try:
            settings_fields = json.loads(settings_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.Setting.from_dict, settings_fields))

    @property
    def builtin_settings(self) -> Sequence[talon.Setting]:
        return tuple(filter(lambda setting: setting.builtin, self.settings))

    @cached_property
    def modes(self) -> Sequence[talon.Mode]:
        modes_json = self.eval_resource("get_modes.py")
        try:
            modes_fields = json.loads(modes_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.Mode.from_dict, modes_fields))

    @property
    def builtin_modes(self) -> Sequence[talon.Mode]:
        return tuple(filter(lambda mode: mode.builtin, self.modes))

    @cached_property
    def tags(self) -> Sequence[talon.Tag]:
        tags_json = self.eval_resource("get_tags.py")
        try:
            tags_fields = json.loads(tags_json)
        except json.JSONDecodeError as e:
            _LOGGER.error(e)
            return ()
        return tuple(map(talon.Tag.from_dict, tags_fields))

    @property
    def builtin_tags(self) -> Sequence[talon.Tag]:
        return tuple(filter(lambda tag: tag.builtin, self.tags))

    @property
    def registry(self) -> Registry:
        registry = Registry()
        registry.extend(self.commands)
        registry.extend(self.actions)
        registry.extend(self.captures)
        registry.extend(self.lists)
        registry.extend(self.settings)
        registry.extend(self.modes)
        registry.extend(self.tags)
        return registry

    @property
    def builtin_registry(self) -> Registry:
        registry = Registry()
        registry.extend(self.builtin_actions)
        registry.extend(self.builtin_captures)
        registry.extend(self.builtin_lists)
        registry.extend(self.builtin_settings)
        registry.extend(self.builtin_modes)
        registry.extend(self.builtin_tags)
        return registry
