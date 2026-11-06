"""Build host runners with Zig or the macOS SDK's Apple Clang."""

import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
COMPILER: Final = (
    ("xcrun", "clang++") if sys.platform == "darwin" else (sys.executable, "-m", "ziglang", "c++")
)


def compile_native(build: Path, sources: tuple[str, ...], flags: tuple[str, ...] = ()) -> Path:
    """Compile repository C++ against test hardware with the host toolchain."""
    executable = build / "runner.exe"
    _ = subprocess.run(  # noqa: S603 - Repository-owned source files and pinned compiler.
        [
            *COMPILER,
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
