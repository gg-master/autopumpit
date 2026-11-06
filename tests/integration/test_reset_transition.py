"""Direct per-pump resets without intermediate mode or schedule transitions."""

from pathlib import Path

from tests.integration.test_core import NOW, run


def test_reset_auto_commits_only_disabled_program(core_binary: Path) -> None:
    # Given two active automatic pumps and enough writes for one journal commit.
    rows = run(
        core_binary,
        "program_prepare",
        "program_reset",
        "program_load 1",
        "program_enable",
        "limit 2",
        f"program_set 0 60 20 {NOW + 1}",
        f"program_set 1 70 20 {NOW + 1}",
        "advance 1000 1",
        "cut 19",
        "reset_pump 0",
        "status",
        "cut -1",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "program_values 1",
        "status",
    )
    # When reset is applied, it must persist disabled directly, not an Auto pause first.
    assert [-1] not in rows
    # Then only the other pump keeps running and reset survives reboot.
    assert rows[4][0] == 2
    assert rows[-3:-1] == [[0, 0], [70, 20]]
    assert rows[-1][6] == 0


def test_reset_manual_cancels_only_selected_and_preserves_remainder(core_binary: Path) -> None:
    # Given two concurrent manual doses and another request waiting.
    rows = run(
        core_binary,
        "boot 1",
        "limit 2",
        "mode 0 1",
        "mode 1 1",
        "mode 2 1",
        "single 0 20",
        "single 1 30",
        "single 2 40",
        "advance 7000 7",
        "reset_pump 0",
        "pump_state 0",
        "duration 0",
        "pump_state 1",
        "pump_state 2",
        "cycle",
        "status",
    )
    # When the selected runtime is reset, its manual mode is cancelled directly.
    assert rows[4:8] == [[0, 0, 0], [13], [1, 1, 23], [1, 1, 0]]
    # Then the other dose keeps its clock and the next FIFO request fills the slot.
    assert rows[-1][0] == 6


def test_duration_edits_cannot_change_pending_doses(core_binary: Path) -> None:
    # Given a working dose and a queued dose.
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 1 1",
        "single 0 20",
        "single 1 30",
        "advance 1000 1",
        "duration_set 0 1",
        "duration_set 1 2",
        "pump_state 0",
        "cancel 0",
        "cycle",
        "pump_state 1",
    )
    # When callers try editing accepted requests, the snapshotted duration remains locked.
    assert rows[-2:] == [[1, 1, 19], [1, 1, 30]]


def test_reselecting_auto_keeps_active_dose_and_capacity_owner(core_binary: Path) -> None:
    # Given one Auto dose is running and another is due under capacity one.
    rows = run(
        core_binary,
        "boot 1",
        f"set 0 60 2 {NOW + 1}",
        f"set 1 60 2 {NOW + 1}",
        "advance 1000 1",
        "mode 0 0",
        "cycle",
        "status",
        "advance 2000 2",
        "status",
    )
    # When Auto is selected again, it must not orphan the already energized output.
    assert [row[0] for row in rows[-2:]] == [1, 2]
