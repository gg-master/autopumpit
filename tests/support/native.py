"""Build host runners with the same pinned compiler on every operating system."""

import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]


def compile_native(build: Path, sources: tuple[str, ...], flags: tuple[str, ...] = ()) -> Path:
    """Compile repository C++ against test hardware without a system toolchain."""
    executable = build / "runner.exe"
    _ = subprocess.run(  # noqa: S603 - Repository-owned source files and pinned compiler.
        [
            sys.executable,
            "-m",
            "ziglang",
            "c++",
            "-std=c++17",
            "-I",
            str(ROOT / "src"),
            "-I",
            str(ROOT / "config"),
            "-I",
            str(ROOT / "tests/support"),
            *flags,
            *(str(ROOT / source) for source in sources),
            "-o",
            str(executable),
        ],
        check=True,
        text=True,
        timeout=180,
    )
    return executable
