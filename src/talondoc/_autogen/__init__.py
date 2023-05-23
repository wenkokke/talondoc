import datetime
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional, Union

import jinja2
import jinja2.sandbox
from typing_extensions import Literal

from talondoc.sphinx import (
    _canonicalize_talon_package,
    _canonicalize_talon_packages,
    _canonicalize_vararg,
)
from talondoc.sphinx.typing import TalonPackage

from .._util.logging import getLogger
from .._util.progress_bar import ProgressBar
from ..analysis.registry import Registry, data
from ..analysis.static import analyse_package

_LOGGER = getLogger(__name__)


# Taken from:
# https://github.com/sphinx-doc/sphinx/blob/5.x/sphinx/ext/autosummary/generate.py
def _underline(title: str, line: str = "=") -> str:
    if "\n" in title:
        raise ValueError("Can only underline single lines")
    return title + "\n" + line * len(title)


def _section(title: str) -> str:
    return _underline(title, line="=")


def _subsection(title: str) -> str:
    return _underline(title, line="-")


def _subsubsection(title: str) -> str:
    return _underline(title, line="^")


def _default_package_name(package_name: Optional[str], package_dir: Path) -> str:
    return package_name or package_dir.parts[-1]


def _default_author(author: Optional[str]) -> str:
    if author:
        return author
    try:
        return subprocess.getoutput("git config --get user.name")
    except subprocess.CalledProcessError:
        return os.getlogin()


def autogen(
    config_dir: Union[str, Path],
    *,
    package_name: Optional[str] = None,
    package_dir: Union[None, str, Path] = None,
    output_dir: Union[None, str, Path] = None,
    template_dir: Union[None, str, Path] = None,
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
    trigger: Optional[Sequence[str]] = None,
    project: Optional[str] = None,
    author: Optional[str] = None,
    release: Optional[str] = None,
    generate_conf: bool = False,
    generate_index: bool = False,
    continue_on_error: bool = True,
    format: Optional[Literal["md", "rst"]] = None,
) -> None:
    # Ensure config_dir is Path:
    if isinstance(config_dir, str):
        config_dir = Path(config_dir).resolve()

    # Ensure output_dir is Path:
    if isinstance(output_dir, str):
        output_dir = Path(output_dir).resolve()

    if output_dir and output_dir.is_absolute():
        _LOGGER.warning(
            f"The output directory should be relative to the configuration directory."
        )
        try:
            output_dir = output_dir.relative_to(config_dir)
        except ValueError as e:
            _LOGGER.error(e)
            exit(1)

    if output_dir:
        output_dir = config_dir / output_dir
    else:
        output_dir = config_dir

    # Check for conf.py:
    conf_py = config_dir / "conf.py"
    sphinx_config: dict[str, Any] = {}
    if conf_py.exists():
        if generate_conf:
            _LOGGER.error(f"The file {conf_py} exists.")
            exit(1)
        try:
            exec(conf_py.read_text(), sphinx_config)
        except BaseException as e:
            _LOGGER.warning(e)

    # Get talon_package from conf.py:
    talon_package: Optional[TalonPackage] = None
    if "talon_package" in sphinx_config:
        talon_package = _canonicalize_talon_package(sphinx_config["talon_package"])
        if talon_package is None:
            _LOGGER.warning(f"Could not read talon_package in {conf_py}.")
    if "talon_packages" in sphinx_config:
        _LOGGER.warning(
            f"The autogen command does not support reading the configuration 'talon_packages'."
        )

    # Resolve package directory:
    if package_dir and isinstance(package_dir, str):
        package_dir = Path(package_dir)

    if (
        package_dir
        and talon_package
        and "path" in talon_package
        and package_dir != (config_dir / talon_package["path"]).resolve()
    ):
        _LOGGER.warning(
            f"The package directory provided differs from the path in {conf_py}."
        )

    if package_dir is None and talon_package and "path" in talon_package:
        package_dir = (config_dir / talon_package["path"]).resolve()

    if package_dir is None:
        _LOGGER.error(
            f"Could not resolve the package directory. "
            f"Please pass --package-dir or add a 'path' to the 'talon_package' "
            f"in {conf_py}"
        )
        exit(1)

    assert isinstance(package_dir, Path)
    print(package_dir)

    # Resolve package name:
    if (
        package_name
        and talon_package
        and "name" in talon_package
        and package_name != talon_package["name"]
    ):
        _LOGGER.warning(
            f"The package name provided differs from the name in {conf_py}."
        )

    if package_name is None and talon_package and "name" in talon_package:
        package_name = talon_package["name"]

    if package_name is None:
        package_name = _default_package_name(package_name, package_dir)

    # Resolve version:
    if (
        project
        and sphinx_config
        and "project" in sphinx_config
        and project != sphinx_config["project"]
    ):
        _LOGGER.warning(f"The project provided differs from the project in {conf_py}.")

    if project is None and sphinx_config and "project" in sphinx_config:
        project = sphinx_config["project"]

    if project is None:
        project = package_name

    # Resolve author:
    if (
        author
        and sphinx_config
        and "author" in sphinx_config
        and author != sphinx_config["author"]
    ):
        _LOGGER.warning(f"The author provided differs from the author in {conf_py}.")

    if author is None and sphinx_config and "author" in sphinx_config:
        author = sphinx_config["author"]

    if author is None:
        author = _default_author(author)

    # Resolve version:
    if (
        release
        and sphinx_config
        and "release" in sphinx_config
        and release != sphinx_config["release"]
    ):
        _LOGGER.warning(f"The release provided differs from the release in {conf_py}.")

    if release is None and sphinx_config and "release" in sphinx_config:
        release = sphinx_config["release"]

    if release is None:
        release = "0.1.0"

    # Resolve include:
    include = _canonicalize_vararg(include)
    if talon_package and "include" in talon_package:
        include = [*include, *_canonicalize_vararg(talon_package["include"])]

    # Resolve exclude:
    exclude = _canonicalize_vararg(exclude)
    if talon_package and "exclude" in talon_package:
        exclude = [*exclude, *_canonicalize_vararg(talon_package["exclude"])]

    # Resolve trigger:
    trigger = _canonicalize_vararg(trigger)
    if talon_package and "trigger" in talon_package:
        trigger = [*trigger, *_canonicalize_vararg(talon_package["trigger"])]

    if not trigger:
        trigger = ["ready"]

    # Resolve format:
    if format is None:
        if (
            sphinx_config
            and "extensions" in sphinx_config
            and "myst_parser" in sphinx_config["extensions"]
        ):
            format = "md"
        else:
            format = "rst"

    # Create jinja2 loaders
    loaders: list[jinja2.BaseLoader] = []
    if template_dir:
        loaders.append(jinja2.FileSystemLoader(template_dir))
    loaders.append(
        jinja2.PackageLoader("talondoc._autogen", "resources", encoding="utf-8")
    )

    # Create jinja2 environment
    env = jinja2.sandbox.SandboxedEnvironment(
        loader=jinja2.ChoiceLoader(loaders),
        autoescape=False,
        keep_trailing_newline=False,
    )
    env.filters["underline"] = _underline
    env.filters["section"] = _section
    env.filters["subsection"] = _subsection
    env.filters["subsubsection"] = _subsubsection

    # Analyse the package
    registry = Registry()
    analyse_package(
        registry=registry,
        package_dir=package_dir,
        package_name=package_name,
        include=include,
        exclude=exclude,
        trigger=trigger,
        show_progress=True,
        continue_on_error=continue_on_error,
    )
    assert package_name in registry.packages
    package: data.Package = registry.get(data.Package, package_name)

    # Make package path relative to output_dir:
    package_path = Path(os.path.relpath(package.location.path, start=config_dir))

    ctx = {
        "project": project,
        "author": author,
        "year": str(datetime.date.today().year),
        "release": release,
        "package_name": package.name,
        "package_path": package_path,
        "include": include,
        "exclude": exclude,
        "trigger": trigger,
        "format": format,
    }

    # Render talon and python file entries:
    template_talon_file = env.get_template(f"talon_file.{format}.jinja2")
    template_python_file = env.get_template(f"python_file.{format}.jinja2")

    toc: list[str] = []
    total: int = len(package.files)
    if generate_conf:
        total += 1
    if generate_index:
        total += 1
    bar = ProgressBar(total=total)
    files: list[data.File] = [
        registry.get(data.File, file_name, referenced_by=package)
        for file_name in package.files
    ]

    def _modules(file: data.File) -> list[data.Module]:
        return [registry.get(data.Module, name) for name in file.modules]

    def _contexts(file: data.File) -> list[data.Context]:
        return [registry.get(data.Context, name) for name in file.contexts]

    # Handle all .talon files:
    talon_files: list[data.File] = [
        file for file in files if file.location.path.parts[-1].endswith(".talon")
    ]
    for file in talon_files:
        # Create path/to/talon/file.{md,rst}:
        bar.step(f" {str(file.location.path)}")
        output_relpath = file.location.path.with_suffix(f".{format}")
        output_path = output_dir / output_relpath
        output_path.parent.mkdir(parents=True, exist_ok=True)

        modules = _modules(file)
        contexts = _contexts(file)

        # Check whether the file has any content
        has_content = any(
            [
                *[module.has_content() for module in modules],
                *[context.has_content() for context in contexts],
            ]
        )

        # Check whether the file defines any commands
        has_commands = any(bool(context.commands) for context in contexts)

        if has_content:
            toc.append(str(output_relpath))
            output_path.write_text(
                template_talon_file.render(
                    file=file,
                    modules=modules,
                    contexts=contexts,
                    has_commands=has_commands,
                    **ctx,
                )
            )

    # Handle all .py files:
    python_files: list[data.File] = [
        file for file in files if file.location.path.parts[-1].endswith(".py")
    ]
    for file in python_files:
        # Create path/to/python/file/api.{md,rst}:
        bar.step(f" {str(file.location.path)}")
        output_relpath = file.location.path.with_suffix("") / f"api.{format}"
        output_path = output_dir / output_relpath
        output_path.parent.mkdir(parents=True, exist_ok=True)

        modules = _modules(file)
        contexts = _contexts(file)

        # Check whether the file has any content
        has_content = any(
            [
                *[module.has_content() for module in modules],
                *[context.has_content() for context in contexts],
            ]
        )

        if has_content:
            toc.append(str(output_relpath))
            output_path.write_text(
                template_python_file.render(
                    file=file,
                    modules=modules,
                    contexts=contexts,
                    **ctx,
                )
            )

    # Create index.{md,rst}
    if generate_index:
        template_index = env.get_template(f"index.{format}.jinja2")
        output_path = output_dir / f"index.{format}"
        bar.step(f" index.{format}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template_index.render(toc=toc, **ctx))

    # Create conf.py
    if generate_conf:
        template_confpy = env.get_template("conf.py.jinja2")
        output_path = output_dir / "conf.py"
        bar.step(" conf.py")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template_confpy.render(**ctx))
