"""GPIO mode changes must not introduce an unintended active transition."""

from pathlib import Path

from tests.integration.test_core import run


def assert_startup_is_inactive(binary: Path) -> None:
    results = run(
        binary,
        "boot 1",
        "transitions",
        "boot 0",
        "transitions",
        "mode 0 1",
        "single 0 2",
        "transitions",
        "advance 2000 2",
        "transitions",
    )
    assert results == [[0], [0], [0], [1], [1]]


def test_active_low_startup_does_not_pulse_outputs(core_binary_low: Path) -> None:
    assert_startup_is_inactive(core_binary_low)


def test_active_high_startup_does_not_pulse_outputs(core_binary: Path) -> None:
    assert_startup_is_inactive(core_binary)
