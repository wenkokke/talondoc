import datetime
import os
import subprocess
from pathlib import Path
from typing import Optional, Union

import jinja2
import jinja2.sandbox

from ..analyze import analyse_package
from ..analyze.entries import PythonFileEntry, TalonFileEntry
from ..analyze.registry import StandaloneRegistry
from ..util.progress_bar import ProgressBar


# Taken from:
# https://github.com/sphinx-doc/sphinx/blob/5.x/sphinx/ext/autosummary/generate.py
def _underline(title: str, line: str = "=") -> str:
    if "\n" in title:
        raise ValueError("Can only underline single lines")
    return title + "\n" + line * len(title)


def _default_package_name(package_name: Optional[str], package_dir: Path) -> str:
    return package_name or package_dir.parts[-1]


def _default_author(author: Optional[str]) -> str:
    if author:
        return author
    try:
        return subprocess.getoutput("git config --get user.name")
    except subprocess.CalledProcessError:
        return os.getlogin()


def generate(
    package_dir: Union[str, Path],
    *,
    package_name: Optional[str] = None,
    output_dir: Union[None, str, Path] = None,
    template_dir: Union[None, str, Path] = None,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    trigger: tuple[str, ...] = (),
    project: Optional[str] = None,
    author: Optional[str] = None,
    release: Optional[str] = None,
    generate_conf: bool = True,
    generate_index: bool = True,
):
    # Set defaults for arguments
    package_dir = Path(package_dir) if isinstance(package_dir, str) else package_dir
    package_name = _default_package_name(package_name, package_dir)
    if output_dir is None:
        output_dir = Path.cwd()
    elif isinstance(output_dir, str):
        output_dir = Path(output_dir)
    project = project or package_name
    author = _default_author(author)
    release = release or "0.1.0"

    # Create jinja2 loaders
    loaders: list[jinja2.BaseLoader] = []
    if template_dir:
        loaders.append(jinja2.FileSystemLoader(template_dir))
    loaders.append(jinja2.PackageLoader("talondoc", "autosummary/template"))

    # Create jinja2 environment
    env = jinja2.sandbox.SandboxedEnvironment(
        loader=jinja2.ChoiceLoader(loaders),
        autoescape=False,
        keep_trailing_newline=False,
    )
    env.filters["underline"] = _underline

    # Analyse the package
    registry = StandaloneRegistry()
    package_entry = analyse_package(
        registry=registry,
        package_dir=package_dir,
        package_name=package_name,
        include=include,
        exclude=exclude,
        trigger=trigger,
        show_progress=True,
    )
    ctx = {
        "project": project,
        "author": author,
        "year": str(datetime.date.today().year),
        "release": release,
        "package_name": package_entry.name,
        "package_path": package_entry.path,
        "include": include,
        "exclude": exclude,
        "trigger": trigger,
    }

    # Make package path relative to output_dir:
    package_entry.path = Path(os.path.relpath(package_entry.path, start=output_dir))

    # Render talon and python file entries:
    template_talon_file_entry = env.get_template("talon_file_entry.rst")
    template_python_file_entry = env.get_template("python_file_entry.rst")
    toc: list[Path] = []
    bar = ProgressBar(total=len(package_entry.files))
    for file_entry in package_entry.files:
        # Create path/to/talon/file.rst:
        if file_entry.path.suffix == ".talon":
            assert isinstance(file_entry, TalonFileEntry)
            bar.step(f" {str(file_entry.path)}")
            output_relpath = file_entry.path.with_suffix(".rst")
            toc.append(output_relpath)
            output_path = output_dir / output_relpath
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                template_talon_file_entry.render(entry=file_entry, **ctx)
            )

        # Create path/to/python/file/api.rst:
        elif file_entry.path.suffix == ".py":
            assert isinstance(file_entry, PythonFileEntry)
            bar.step(f" {str(file_entry.path)}")
            output_relpath = file_entry.path.with_suffix("") / "api.rst"
            toc.append(output_relpath)
            output_path = output_dir / output_relpath
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                template_python_file_entry.render(entry=file_entry, **ctx)
            )

        # Skip file entry:
        else:
            bar.step()

    # Create index.rst
    if generate_index:
        template_index = env.get_template("index.rst")
        output_path = output_dir / "index.rst"
        bar.step(" index.rst")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template_index.render(toc=toc, **ctx))

    # Create conf.py
    if generate_conf:
        template_confpy = env.get_template("conf.py")
        output_path = output_dir / "conf.py"
        bar.step(" conf.py")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template_confpy.render(**ctx))