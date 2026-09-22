"""Interface for ``python -m fastcs_carbide``."""

from fastcs.launch import launch

from fastcs_carbide.controller import CarbideController

from . import __version__

__all__ = ["main"]


def main() -> None:
    launch(CarbideController, version=__version__)


if __name__ == "__main__":
    main()
