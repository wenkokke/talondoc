from typing import Optional

import click

from ._version import __version__
from .autogen import autogen
from .cache_builtin import cache_builtin


@click.group(name="talondoc")
@click.version_option(
    package_name="talondoc",
    version=__version__,
)
def talondoc():
    pass


@talondoc.command(name="autogen")
@click.argument(
    "package-dir",
    type=click.Path(),
)
@click.option(
    "-p",
    "--package-name",
    type=str,
    default=None,
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(),
)
@click.option(
    "--sphinx-root",
    type=click.Path(),
)
@click.option(
    "-t",
    "--template-dir",
    type=click.Path(),
    default=None,
)
@click.option(
    "--include",
    type=click.Path(),
    multiple=True,
    default=[],
)
@click.option(
    "--exclude",
    type=click.Path(),
    multiple=True,
    default=[],
)
@click.option(
    "--trigger",
    type=str,
    multiple=True,
    default=["ready"],
)
@click.option(
    "--project",
    type=str,
    default=None,
)
@click.option(
    "--author",
    type=str,
    default=None,
)
@click.option(
    "--release",
    type=str,
    default=None,
)
@click.option(
    "--generate-conf/--no-generate-conf",
    default=True,
)
@click.option(
    "--generate-index/--no-generate-index",
    default=True,
)
@click.option(
    "--continue-on-error/--no-continue-on-error",
    default=True,
)
def _autogen(
    package_dir: str,
    *,
    output_dir: str,
    sphinx_root: str,
    template_dir: Optional[str],
    package_name: Optional[str],
    include: list[str],
    exclude: list[str],
    trigger: list[str],
    project: Optional[str],
    author: Optional[str],
    release: Optional[str],
    generate_conf: bool,
    generate_index: bool,
    continue_on_error: bool,
):
    autogen(
        package_dir,
        output_dir=output_dir,
        sphinx_root=sphinx_root,
        template_dir=template_dir,
        package_name=package_name,
        include=tuple(include),
        exclude=tuple(exclude),
        trigger=tuple(trigger),
        project=project,
        author=author,
        release=release,
        generate_conf=generate_conf,
        generate_index=generate_index,
        continue_on_error=continue_on_error,
    )


@talondoc.command(name="cache_builtin")
@click.argument(
    "output_dir",
    type=click.Path(),
)
def _cache_builtin(output_dir: str):
    cache_builtin(output_dir=output_dir)


if __name__ == "__main__":
    talondoc()
