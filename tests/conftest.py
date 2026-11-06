"""Build the real firmware core with the host test compiler."""

import subprocess
from pathlib import Path

import pytest

from tests.support.native import COMPILER


def build_core(tmp_path_factory: pytest.TempPathFactory, *, active_low: bool = False) -> Path:
    """Compile real scheduler and pumping code against narrow hardware fakes."""
    root = Path(__file__).resolve().parents[1]
    build = tmp_path_factory.mktemp("native")
    executable = build / "core.exe"
    settings = (root / "config/settings.h").read_text(encoding="utf-8")
    if active_low:
        settings = settings.replace("#define SWITCH_LEVEL 1", "#define SWITCH_LEVEL 0")
    _ = (build / "settings.h").write_text(settings, encoding="utf-8")
    _ = subprocess.run(  # noqa: S603 - Executable and sources are repository-controlled.
        [
            *COMPILER,
            "-std=c++17",
            "-I",
            str(root / "src"),
            "-I",
            str(build),
            str(root / "src/core/pump_control.cpp"),
            str(root / "src/core/concurrency_settings.cpp"),
            str(root / "src/core/application.cpp"),
            str(root / "src/core/rtc_schedule.cpp"),
            str(root / "src/core/program_settings.cpp"),
            str(root / "tests/support/fake_hardware.cpp"),
            str(root / "tests/integration/harness.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
        text=True,
        timeout=180,
    )
    return executable


@pytest.fixture(scope="session")
def core_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_core(tmp_path_factory)


@pytest.fixture(scope="session")
def core_binary_low(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_core(tmp_path_factory, active_low=True)
