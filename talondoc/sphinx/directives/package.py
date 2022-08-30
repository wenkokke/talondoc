from pathlib import Path
from typing import NoReturn, Optional, cast
from sphinx.directives import SphinxDirective
from sphinx.util.typing import OptionSpec
from ...analyze.registry import Registry
from ...analyze import Registry, analyse_package


def optional_strlist(argument: Optional[str]) -> tuple[str, ...]:
    if argument:
        return tuple(pattern.strip() for pattern in argument.split(","))
    else:
        return ()


def optional_str(argument: Optional[str]) -> Optional[str]:
    if argument:
        return argument.strip()
    else:
        return None


class TalonPackageDirective(SphinxDirective):

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    option_spec: OptionSpec = {
        "name": optional_str,
        "include": optional_strlist,
        "exclude": optional_strlist,
    }
    final_argument_whitespace = False

    def run(self) -> list[NoReturn]:
        name: Optional[str] = self.options.get("name")
        include: tuple[str, ...] = self.options.get("include", ())
        exclude: tuple[str, ...] = self.options.get("exclude", ())
        analyse_package(
            registry=cast(Registry, self.env.get_domain("talon")),
            package_root=Path(self.arguments[0].strip()),
            name=name,
            include=tuple(include),
            exclude=tuple(exclude),
        ),
        return []
