from pathlib import Path

from tests.integration.test_core import NOW, run


def test_fresh_start_reset_and_marker(core_binary: Path) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "program_required",
        "program_reset",
        "program_load 1",
        "program_values 0",
        "peek 1023",
        "program_enable",
        "program_required",
        "peek 1023",
    )
    assert results == [[1], [1], [0, 0], [0], [0], [5]]


def test_settings_roundtrip_and_reset(core_binary: Path) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "program_reset",
        "program_load 1",
        "program_enable",
        f"program_set 0 30 2 {NOW + 60}",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "program_reset",
        "program_prepare",
        "program_load 1",
        "program_values 0",
        "status",
    )
    assert results[:4] == [[1], [0], [1], [30, 2]]
    assert results[4:6] == [[1], [0, 0]]
    assert results[-1][6:] == [0] * 14


def test_failed_save_keeps_program_settings(core_binary: Path) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "program_reset",
        "program_load 1",
        "program_enable",
        f"program_set 0 30 2 {NOW - 1}",
        "program_values 0",
        "mode 0 1",
        "single 0 2",
        f"program_set 0 30 2 {NOW + 1}",
        "program_values 0",
    )
    assert results == [[1], [2], [0, 0], [0], [1], [0, 0]]
