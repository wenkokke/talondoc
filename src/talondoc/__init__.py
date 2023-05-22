import os
from typing import Optional

import click
from typing_extensions import Literal

from ._autogen import autogen
from ._cache_builtin import cache_builtin
from ._util import logging
from ._version import __version__

################################################################################
# TalonDoc CLI
################################################################################


@click.group(name="talondoc")
@click.version_option(
    prog_name="talondoc",
    version=__version__,
)
@click.option(
    "--log-level",
    type=click.Choice(["ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False),
    default="INFO",
)
def talondoc(*, log_level: Literal["ERROR", "WARNING", "INFO", "DEBUG"]) -> None:
    logging.basicConfig(
        level={
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }.get(log_level.upper(), logging.INFO),
    )
    pass


################################################################################
# TalonDoc CLI - Autogen
################################################################################


@talondoc.command(name="autogen")
@click.option(
    "--package-name",
    type=str,
    default=None,
)
@click.option(
    "--package-dir",
    type=click.Path(),
    required=True,
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
    default=bool(os.environ.get("TALONDOC_STRICT", False)),
)
@click.option(
    "--format",
    type=click.Choice(["rst", "md"]),
    default="rst",
)
def _autogen(
    *,
    output_dir: str,
    sphinx_root: str,
    template_dir: Optional[str],
    package_dir: str,
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
    format: Literal["rst", "md"],
) -> None:
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
        format=format,
    )


################################################################################
# TalonDoc CLI - Build
################################################################################


@talondoc.command(name="build")
@click.argument(
    "source_dir",
    type=click.Path(),
)
@click.argument(
    "output_dir",
    type=click.Path(),
)
def _build(
    source_dir: str,
    output_dir: str,
) -> None:
    import sphinx.cmd.build

    # NOTE: We always clean before building, as TalonDoc's support for
    #       merging Sphinx build environments is still under development.
    exitcode = sphinx.cmd.build.build_main(["-M", "clean", source_dir, output_dir])
    if exitcode != 0:
        exit(exitcode)

    exitcode = sphinx.cmd.build.build_main(["-M", "html", source_dir, output_dir])
    if exitcode != 0:
        exit(exitcode)


################################################################################
# TalonDoc CLI - Cache Builtin
################################################################################


@talondoc.command(name="cache_builtin")
@click.argument(
    "output_dir",
    type=click.Path(),
)
def _cache_builtin(
    output_dir: str,
) -> None:
    cache_builtin(output_dir=output_dir)


if __name__ == "__main__":
    talondoc()
