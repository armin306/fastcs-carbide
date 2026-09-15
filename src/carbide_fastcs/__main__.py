"""Interface for ``python -m carbide_fastcs``."""

from functools import cache
from pathlib import Path
from typing import Annotated

import typer
from fastcs.launch import FastCS
from fastcs.transport.epics.options import EpicsIOCOptions, EpicsOptions

from carbide_fastcs.connection import DEFAULT_BASE_URL
from carbide_fastcs.controller import CarbideController

from . import __version__

__all__ = ["main"]

CWD_AT_LOADING = Path.cwd()
app = typer.Typer()


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="..."),
    ] = None,
) -> None:
    pass


def create_ui_and_docs(
    controller: CarbideController, prefix: str, output_path: Path
) -> None:
    from fastcs.transport.epics.docs import EpicsDocs, EpicsDocsOptions
    from fastcs.transport.epics.gui import EpicsGUI, EpicsGUIOptions

    gui = EpicsGUI(controller, prefix)
    gui.create_gui(EpicsGUIOptions(output_path / "index.bob"))
    docs = EpicsDocs(controller)
    docs.create_docs(EpicsDocsOptions(output_path / "index.md"))


@app.command()
def ioc(
    pv_prefix: Annotated[str, typer.Argument(help="Name of the IOC")] = "CARBIDE",
    base_url: Annotated[
        str, typer.Argument(help="Base URL of the CARBIDE Supervisor REST API")
    ] = DEFAULT_BASE_URL,
    output_path: Annotated[
        Path,
        typer.Option(
            help="folder of local service definition",
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ] = CWD_AT_LOADING,
) -> None:
    """Start up the service."""
    controller = get_controller(base_url)
    create_ui_and_docs(controller, pv_prefix, output_path)

    epics_options = EpicsOptions(ioc=EpicsIOCOptions(pv_prefix=pv_prefix))
    fastcs = FastCS(controller, epics_options)
    fastcs.run()


@cache
def get_controller(base_url: str) -> CarbideController:
    return CarbideController(base_url)


if __name__ == "__main__":
    app()
