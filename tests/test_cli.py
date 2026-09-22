import subprocess
import sys

from fastcs_carbide import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "fastcs_carbide", "--version"]
    assert f"CarbideController: {__version__}" in subprocess.check_output(cmd).decode()
