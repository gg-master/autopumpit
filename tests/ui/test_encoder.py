import subprocess
from pathlib import Path

import pytest

from tests.support.native import ROOT, compile_native


@pytest.fixture(scope="module")
def encoder_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return compile_native(
        tmp_path_factory.mktemp("encoder"),
        (
            "src/ui/lcd/encoder_input.cpp",
            "lib/GyverEncoder/src/GyverEncoder.cpp",
            "tests/ui/encoder_harness.cpp",
        ),
        ("-I", str(ROOT / "lib/GyverEncoder/src")),
    )


def events(binary: Path, samples: list[str]) -> list[tuple[int, int]]:
    result = subprocess.run(  # noqa: S603 - Repository-built real encoder driver.
        [str(binary)],
        input="\n".join(samples),
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    values: list[tuple[int, int]] = []
    for row in result.stdout.splitlines():
        timestamp, event = row.split()
        values.append((int(timestamp), int(event)))
    return values


def test_short_press_opens_mode_menu_without_hold(encoder_binary: Path) -> None:
    assert events(encoder_binary, ["100 1 1 1", "200 0 1 1", "300 1 1 1", "400 1 1 1"]) == [
        (300, 4)
    ]


def test_long_press_resets_on_release_only_once(encoder_binary: Path) -> None:
    samples = ["100 1 1 1", "200 0 1 1", "901 0 1 1", "950 0 1 1", "1000 1 1 1", "1100 1 1 1"]
    assert events(encoder_binary, samples) == [(1000, 5)]


@pytest.mark.parametrize("start", [300, 1000])
def test_held_rotation_cannot_trigger_reset(encoder_binary: Path, start: int) -> None:
    samples = ["100 1 1 1", "200 0 1 1"]
    if start > 900:
        samples += ["901 0 1 1"]
    samples += [
        f"{start} 0 1 0",
        f"{start + 50} 0 0 0",
        f"{start + 100} 0 0 1",
        f"{start + 150} 0 1 1",
        f"{start + 300} 1 1 1",
        f"{start + 400} 1 1 1",
    ]
    recorded = events(encoder_binary, samples)
    assert recorded
    assert all(event in (2, 3) for _, event in recorded)


def test_each_separate_hold_produces_one_reset(encoder_binary: Path) -> None:
    samples = [
        "100 1 1 1",
        "200 0 1 1",
        "901 0 1 1",
        "1000 1 1 1",
        "1200 0 1 1",
        "1901 0 1 1",
        "2000 1 1 1",
        "2200 1 1 1",
    ]
    assert events(encoder_binary, samples) == [(1000, 5), (2000, 5)]
