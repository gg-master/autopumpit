"""Run the same complete quality gate locally and in CI."""

import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
COMMANDS: Final = (
    ("ruff", "check", "tools", "tests"),
    ("ruff", "format", "--check", "tools", "tests"),
    ("basedpyright",),
    ("pytest",),
    ("tools.check_translations",),
    ("platformio", "run", "-e", "uno", "-e", "uno-ds3231", "-e", "uno-en", "-e", "uno-ds3231-en"),
)


def main() -> int:
    """Stop at the first failed check and propagate its exit code."""
    for command in COMMANDS:
        print("\n> python -m " + " ".join(command), flush=True)
        result = subprocess.run(  # noqa: S603 - Fixed commands from the locked environment.
            [sys.executable, "-m", *command],
            cwd=ROOT,
            check=False,
            timeout=600,
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
