"""Persistence failure scenarios against the real two-slot EEPROM journal."""

from pathlib import Path

import pytest

from tests.integration.test_core import NOW, run


@pytest.mark.parametrize("cut", range(19))
def test_torn_commit_falls_back_when_power_fails_at_each_write(core_binary: Path, cut: int) -> None:
    # Given a saved deadline and an automatic dose ready to start.
    # When each individual commit write is interrupted by power loss.
    results = run(
        core_binary,
        "boot 1",
        f"set 0 100 10 {NOW + 1}",
        f"cut {cut}",
        "advance 1000 1",
        "status",
        "cut -1",
        "boot 0",
        "status",
    )
    # Then the relay never energizes before a complete journal commit.
    assert results[-2][0] == 0
    assert results[-1][0] == 0
    assert results[-1][6] == NOW + 1


@pytest.mark.parametrize("byte", range(18))
def test_crc_rejects_corruption_when_any_record_byte_changes(core_binary: Path, byte: int) -> None:
    # Given the latest record enables channel zero while the older record is disabled.
    # When one byte of the latest record is corrupted.
    results = run(
        core_binary,
        "boot 1",
        f"set 0 100 10 {NOW + 1}",
        f"corrupt {146 + byte} 1",
        "boot 0",
        "status",
    )
    # Then the valid older slot is loaded instead of the corrupt new configuration.
    assert results[-1][6] == 0


@pytest.mark.parametrize("outage_seconds", [5, 30])
def test_deadline_is_retained_when_outage_ends_before_or_after_due(
    core_binary: Path,
    outage_seconds: int,
) -> None:
    # Given a future automatic deadline.
    # When reboot occurs before or after that deadline.
    results = run(
        core_binary,
        "boot 1",
        f"set 0 100 10 {NOW + 20}",
        f"time 1000 {NOW + outage_seconds}",
        "boot 0",
        "cycle",
        "status",
    )
    # Then a future deadline remains future and an overdue dose starts once.
    assert results[-1][0] == (0 if outage_seconds < 20 else 1)
    assert results[-1][6] == (NOW + 20 if outage_seconds < 20 else NOW + 140)
