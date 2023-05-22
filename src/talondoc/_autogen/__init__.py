import datetime
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Optional, Union

import jinja2
import jinja2.sandbox
from typing_extensions import Literal

from .._util.progress_bar import ProgressBar
from ..analysis.registry import Registry, data
from ..analysis.static import analyse_package


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
    package_dir: Union[str, Path],
    *,
    package_name: Optional[str] = None,
    sphinx_root: Union[None, str, Path] = None,
    output_dir: Union[None, str, Path] = None,
    template_dir: Union[None, str, Path] = None,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    trigger: Sequence[str] = (),
    project: Optional[str] = None,
    author: Optional[str] = None,
    release: Optional[str] = None,
    generate_conf: bool = True,
    generate_index: bool = True,
    continue_on_error: bool = True,
    format: Literal["md", "rst"] = "rst",
) -> None:
    # Set defaults for arguments
    if isinstance(package_dir, str):
        package_dir = Path(package_dir)
    package_name = _default_package_name(package_name, package_dir)
    if isinstance(sphinx_root, str):
        sphinx_root = Path(sphinx_root)
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    if sphinx_root is None:
        sphinx_root = output_dir if output_dir else Path.cwd()
    if output_dir is None:
        output_dir = sphinx_root
    project = project or package_name
    author = _default_author(author)
    release = release or "0.1.0"

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
    package_path = Path(os.path.relpath(package.location.path, start=sphinx_root))

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

    toc: list[Path] = []
    total: int = len(package.files)
    if generate_conf:
        total += 1
    if generate_index:
        total += 1
    bar = ProgressBar(total=total)
    for file_name in package.files:
        file: data.File = registry.get(data.File, file_name, referenced_by=package)

        # Get all modules
        modules: list[data.Module] = []
        for module_name in file.modules:
            module = registry.lookup(data.Module, module_name)
            if module:
                modules.append(module)

        # Get all contexts
        contexts: list[data.Context] = []
        for context_name in file.contexts:
            context = registry.lookup(data.Context, context_name)
            if context:
                contexts.append(context)

        # Create path/to/talon/file.{md,rst}:
        if file.location.path.suffix == ".talon":
            bar.step(f" {str(file.location.path)}")
            output_relpath = file.location.path.with_suffix(f".{format}")
            toc.append(output_relpath)
            output_path = output_dir / output_relpath
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Check whether the file defines any commands
            has_commands = any(bool(context.commands) for context in contexts)

            output_path.write_text(
                template_talon_file.render(
                    file=file,
                    modules=modules,
                    contexts=contexts,
                    has_commands=has_commands,
                    **ctx,
                )
            )

        # Create path/to/python/file/api.{md,rst}:
        elif file.location.path.suffix == ".py":
            bar.step(f" {str(file.location.path)}")
            output_relpath = file.location.path.with_suffix("") / f"api.{format}"
            toc.append(output_relpath)
            output_path = output_dir / output_relpath
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                template_python_file.render(
                    file=file,
                    modules=modules,
                    contexts=contexts,
                    **ctx,
                )
            )

        # Skip file entry:
        else:
            bar.step()

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
