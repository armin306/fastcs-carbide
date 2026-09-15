import subprocess
import sys

from carbide_fastcs import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "carbide_fastcs", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
