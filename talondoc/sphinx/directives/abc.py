import typing
from collections.abc import Iterator
from ...entries import CommandEntry, PackageEntry, TalonFileEntry
from ...util.logging import getLogger
from .command import include_command
import sphinx.directives

_logger = getLogger(__name__)

if typing.TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = typing.Any


class TalonDocDirective(sphinx.directives.SphinxDirective):
    @property
    def talon(self) -> TalonDomain:
        return typing.cast(TalonDomain, self.env.get_domain("talon"))


class TalonDocObjectDescription(sphinx.directives.ObjectDescription, TalonDocDirective):
    pass


class TalonCommandListDirective(TalonDocDirective):
    def find_package(self) -> PackageEntry:
        namespace = self.options.get("package")
        candidate = self.talon.currentpackage
        if candidate and (not namespace or candidate.namespace == namespace):
            return candidate
        candidate = self.talon.packages.get(namespace, None)
        if candidate:
            return candidate
        raise ValueError(f"Could not find package '{namespace}'")

    def find_file(
        self, sig: str, *, package_entry: typing.Optional[PackageEntry] = None
    ) -> TalonFileEntry:
        # Find the package:
        if package_entry is None:
            try:
                package_entry = self.find_package()
            except ValueError as e:
                raise ValueError(f"Could not find file '{sig}'", e)

        # Find the file:
        for file in package_entry.files:
            if isinstance(file, TalonFileEntry):
                if (
                    sig == file.name
                    or sig == str(file.path)
                    or f"{sig}.talon" == file.name
                    or f"{sig}.talon" == str(file.path)
                ):
                    return file
        raise ValueError(f"Could not find file '{sig}'")

    def find_commands(self) -> Iterator[CommandEntry]:
        exclude = self.options.get("exclude", ())
        include = self.options.get("include", ())

        if self.arguments:
            # If file arguments were given, return all commands in that file
            # which have not been explicitly excluded:
            for sig in self.arguments:
                for command in self.find_file(sig).commands:
                    if include_command(
                        command, default="include", exclude=exclude, include=include
                    ):
                        yield command
        else:
            # If no file arguments were given, return all commands in the package
            # which have been explicitly included:
            for command in self.talon.commands:
                if include_command(
                    command, default="exclude", exclude=exclude, include=include
                ):
                    yield command

    def caption(self) -> Iterator[str]:
        # Get caption from options
        caption = self.options.get("caption", None)
        if caption:
            yield caption
            return
        # Get caption from file name
        if len(self.arguments) == 1:
            file = self.find_file(self.arguments[0])
            yield file.name.removesuffix(".talon")
            return
