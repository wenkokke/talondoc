from typing import Optional

import click

from .autosummary.generate import generate

from .preprocessing.builtin_extractor import extract_builtin

__version__: str = "0.1.1"


@click.group(name="talondoc")
@click.version_option(
    package_name="talondoc",
    version=__version__,
)
def cli():
    pass


@cli.command(name="autogen")
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
def autogen(
    package_dir: str,
    *,
    output_dir: str,
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
):
    generate(
        package_dir,
        output_dir=output_dir,
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
    )


@cli.command(name="preprocess")
@click.argument(
    "output_dir",
    type=click.Path(),
)
def preprocess(output_dir: str):
    extract_builtin(output_dir=output_dir)


if __name__ == "__main__":
    cli()
