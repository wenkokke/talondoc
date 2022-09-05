import jinja2
import pkg_resources # type: ignore

from pathlib import Path
from typing import Optional, Union
from ..analyze.registry import StandaloneRegistry
from ..analyze import analyse_package

# Taken from:
# https://github.com/sphinx-doc/sphinx/blob/5.x/sphinx/ext/autosummary/generate.py
#
def _underline(title: str, line: str = "=") -> str:
    if "\n" in title:
        raise ValueError("Can only underline single lines")
    return title + "\n" + line * len(title)


def _default_package_name(package_name: Optional[str], package_dir: Path) -> str:
    return package_name or package_dir.parts[-1]


def _default_template_index(template_index: Union[None, str, Path]) -> Path:
    if template_index is None:
        template_index = pkg_resources.resource_filename(
            "talondoc", "autosummary/template/index.rst"
        )
    if isinstance(template_index, str):
        template_index = Path(template_index)
    return template_index


def _default_template_talon(template_talon: Union[None, str, Path]) -> Path:
    if template_talon is None:
        template_talon = pkg_resources.resource_filename(
            "talondoc", "autosummary/template/talon.rst"
        )
    if isinstance(template_talon, str):
        template_talon = Path(template_talon)
    return template_talon


def generate(
    package_dir: Union[str, Path],
    *,
    package_name: Optional[str],
    output_dir: Union[str, Path],
    template_index: Union[None, str, Path],
    template_talon: Union[None, str, Path],
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    trigger: tuple[str, ...] = (),
):
    # Set defaults for arguments
    package_dir = Path(package_dir) if isinstance(package_dir, str) else package_dir
    package_name = _default_package_name(package_name, package_dir)
    output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
    template_index = _default_template_index(template_index)
    template_talon = _default_template_talon(template_talon)

    # Create a jinja2 environment
    env = jinja2.Environment()
    env.filters["underline"] = _underline

    # Analyse the package
    registry = StandaloneRegistry()
    analyse_package(
        registry=registry,
        package_dir=package_dir,
        package_name=package_name,
        include=include,
        exclude=exclude,
        trigger=trigger,
    )
