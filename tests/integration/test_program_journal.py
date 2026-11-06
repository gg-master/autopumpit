"""The program journal is the sole authoritative persistent configuration."""

from pathlib import Path

import pytest

from tests.integration.test_core import NOW, run


def test_legacy_bytes_are_ignored_and_never_updated(core_binary: Path) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "poke 0 30",
        "poke 4 2",
        "program_load 0",
        "program_enable",
        "program_values 0",
        f"program_set 0 60 7 {NOW + 40}",
        "peek 0",
        "peek 4",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "status",
    )
    assert results[:-1] == [[1], [0, 0], [0], [30], [2], [1], [60, 7]]
    assert results[-1][6] == NOW + 40


@pytest.mark.parametrize("cut", range(19))
def test_interrupted_edit_keeps_previous_program_in_ram_and_storage(
    core_binary: Path, cut: int
) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "program_load 1",
        "program_enable",
        f"program_set 0 30 2 {NOW + 40}",
        f"cut {cut}",
        f"program_set 0 60 7 {NOW + 80}",
        "program_values 0",
        "status",
        "cut -1",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "status",
    )
    assert results[2:4] == [[-1], [30, 2]]
    assert results[4][6] == NOW + 40
    assert results[6] == [30, 2]
    assert results[7][6] == NOW + 40


def test_missing_both_records_disables_channel_instead_of_using_old_bytes(
    core_binary: Path,
) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "program_load 1",
        "program_enable",
        f"program_set 0 30 2 {NOW + 40}",
        "poke 128 0",
        "poke 146 0",
        "poke 0 30",
        "poke 4 2",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "status",
    )
    assert results[-2] == [0, 0]
    assert results[-1][6] == 0


def test_program_is_loaded_even_while_clock_requires_confirmation(core_binary: Path) -> None:
    results = run(
        core_binary,
        "program_prepare",
        "program_load 1",
        "program_enable",
        f"program_set 0 30 2 {NOW + 40}",
        "fault 1 1",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "status",
        f"program_clock {NOW + 10}",
        "program_values 0",
        "status",
    )
    assert results[3] == results[6] == [30, 2]
    assert results[4][5:7] == [1, NOW + 40]
    assert results[7][5:7] == [0, NOW + 40]
