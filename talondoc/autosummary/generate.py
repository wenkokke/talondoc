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
    author: Optional[str] = None,
    release: Optional[str] = None,
):
    # Set defaults for arguments
    package_dir = Path(package_dir) if isinstance(package_dir, str) else package_dir
    package_name = _default_package_name(package_name, package_dir)
    if output_dir is None:
        output_dir = Path.cwd()
    elif isinstance(output_dir, str):
        output_dir = Path(output_dir)
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
    )
    env.filters["underline"] = _underline

    # Analyse the package
    print(f"Analyse '{package_name}:{package_dir}'")
    registry = StandaloneRegistry()
    package_entry = analyse_package(
        registry=registry,
        package_dir=package_dir,
        package_name=package_name,
        include=include,
        exclude=exclude,
        trigger=trigger,
    )

    template_index = env.get_template("index.rst")
    template_confpy = env.get_template("conf.py")
    template_talon_file_entry = env.get_template("talon_file_entry.rst")
    template_python_file_entry = env.get_template("python_file_entry.rst")
    toc: list[Path] = []
    for file_entry in package_entry.files:
        # Create path/to/talon/file/api.rst
        if file_entry.path.suffix == ".talon":
            assert isinstance(file_entry, TalonFileEntry)
            output_relpath = file_entry.path.with_suffix(".rst")
            toc.append(output_relpath)
            print(f"Write {output_relpath}")
            output_path = output_dir / output_relpath
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(template_talon_file_entry.render(entry=file_entry))

        # Create path/to/python/file/api.rst
        if file_entry.path.suffix == ".py":
            assert isinstance(file_entry, PythonFileEntry)
            output_relpath = file_entry.path.with_suffix("") / "api.rst"
            toc.append(output_relpath)
            print(f"Write {output_relpath}")
            output_path = output_dir / output_relpath
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(template_python_file_entry.render(entry=file_entry))

    # Create index.rst
    output_path = output_dir / "index.rst"
    print(f"Write index.rst")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        template_index.render(
            name=package_entry.name,
            path=str(package_entry.path),
            toc=toc,
            include=include,
            exclude=exclude,
            trigger=trigger,
        )
    )

    # Create conf.py
    output_path = output_dir / "conf.py"
    print(f"Write conf.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        template_confpy.render(
            project=package_entry.name,
            author=author,
            year=str(datetime.date.today().year),
            release=release,
        )
    )
