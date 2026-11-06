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
    assert events(encoder_binary, ["100 1 1 1", "200 0 1 1", "300 1 1 1", "600 1 1 1"]) == [
        (600, 4)
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


def test_double_click_is_one_back_event_without_forward_click(encoder_binary: Path) -> None:
    samples = ["100 1 1 1", "200 0 1 1", "300 1 1 1", "400 0 1 1", "500 1 1 1", "900 1 1 1"]
    assert events(encoder_binary, samples) == [(500, 6)]


def test_single_click_waits_for_double_click_window(encoder_binary: Path) -> None:
    samples = ["100 1 1 1", "200 0 1 1", "300 1 1 1", "599 1 1 1", "600 1 1 1"]
    assert events(encoder_binary, samples) == [(600, 4)]


def test_two_slow_clicks_are_both_delivered_even_with_sparse_polling(encoder_binary: Path) -> None:
    samples = ["100 1 1 1", "200 0 1 1", "300 1 1 1", "650 0 1 1", "800 1 1 1", "1100 1 1 1"]
    assert events(encoder_binary, samples) == [(650, 4), (1100, 4)]


def test_click_window_handles_millis_wrap(encoder_binary: Path) -> None:
    samples = ["4294966900 1 1 1", "4294967000 0 1 1", "4294967200 1 1 1", "203 1 1 1", "204 1 1 1"]
    assert events(encoder_binary, samples) == [(204, 4)]


@pytest.mark.parametrize("release", [599, 600])
def test_double_click_includes_window_boundary(encoder_binary: Path, release: int) -> None:
    samples = ["100 1 1 1", "200 0 1 1", "300 1 1 1", "400 0 1 1", f"{release} 1 1 1", "1000 1 1 1"]
    assert events(encoder_binary, samples) == [(release, 6)]


def test_clicks_outside_window_remain_separate(encoder_binary: Path) -> None:
    samples = ["100 1 1 1", "200 0 1 1", "300 1 1 1", "400 0 1 1", "601 1 1 1", "901 1 1 1"]
    assert events(encoder_binary, samples) == [(601, 4), (901, 4)]


def test_triple_click_produces_back_then_single(encoder_binary: Path) -> None:
    samples = [
        "100 1 1 1",
        "200 0 1 1",
        "300 1 1 1",
        "400 0 1 1",
        "500 1 1 1",
        "600 0 1 1",
        "700 1 1 1",
        "1000 1 1 1",
    ]
    assert events(encoder_binary, samples) == [(500, 6), (1000, 4)]
