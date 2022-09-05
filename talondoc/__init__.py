from typing import Optional
import click
from .autosummary.generate import generate

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
    "--template-index",
    type=click.Path(),
    default=None,
)
@click.option(
    "--template-talon",
    type=click.Path(),
    default=None,
)
def autogen(
    package_dir: str,
    *,
    package_name: Optional[str],
    output_dir: str,
    template_index: Optional[str],
    template_talon: Optional[str],
):
    generate(
        package_dir,
        package_name=package_name,
        output_dir=output_dir,
        template_index=template_index,
        template_talon=template_talon,
    )


if __name__ == "__main__":
    cli()
