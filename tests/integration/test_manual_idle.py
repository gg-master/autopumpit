from pathlib import Path

import pytest

from tests.integration.test_core import NOW, run


def test_stop_remembers_remaining_and_completion_restores_original(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "duration_set 0 20",
        "single 0 20",
        "advance 7500 7",
        "cancel 0",
        "duration 0",
        "mode 0 0",
        "mode 0 1",
        "duration 0",
        "single 0 13",
        "advance 13000 13",
        "duration 0",
    )
    assert rows == [[0], [13], [13], [0], [20]]


def test_explicit_auto_during_run_captures_remaining(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "duration_set 0 20",
        "single 0 20",
        "advance 8000 8",
        "mode 0 0",
        "duration 0",
        "status",
        "mode 0 1",
        "duration 0",
    )
    assert rows[1] == rows[3] == [12]
    assert rows[2][0] == 0


def test_idle_timeout_keeps_unstarted_duration_and_original_due(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        f"set 0 60 2 {NOW + 400}",
        "mode 0 1",
        "duration_set 0 17",
        "advance 89999 89",
        "pump_state 0",
        "advance 1 1",
        "pump_state 0",
        "duration 0",
        "status",
    )
    assert rows[1] == [1, 0, 0]
    assert rows[2] == [0, 0, 0]
    assert rows[3] == [17]
    assert rows[4][6] == NOW + 400


def test_each_idle_timer_is_independent_of_other_pump_actions(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 1 1",
        "advance 60000 60",
        "touch 1",
        "advance 30000 30",
        "pump_state 0",
        "pump_state 1",
        "advance 60000 60",
        "pump_state 1",
    )
    assert rows == [[0, 0, 0], [1, 0, 0], [0, 0, 0]]


def test_active_and_queued_requests_never_expire_for_inactivity(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 1 1",
        "single 0 600",
        "single 1 7",
        "advance 400000 400",
        "pump_state 0",
        "pump_state 1",
        "advance 200000 200",
        "pump_state 1",
        "duration 0",
        "advance 7000 7",
        "duration 1",
        "advance 83000 83",
        "pump_state 0",
        "pump_state 1",
        "advance 7000 7",
        "pump_state 1",
    )
    assert rows[2] == [1, 1, 200]
    assert rows[3] == [1, 1, 0]
    assert rows[4] == [1, 1, 7]
    assert rows[5:7] == [[600], [7]]
    assert rows[7:10] == [[0, 0, 0], [1, 0, 0], [0, 0, 0]]


def test_stopped_pump_gets_full_idle_period_and_retains_remainder(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "single 0 600",
        "advance 400000 400",
        "cancel 0",
        "advance 89999 89",
        "pump_state 0",
        "advance 1 1",
        "pump_state 0",
        "duration 0",
    )
    assert rows[1:] == [[1, 0, 0], [0, 0, 0], [200]]


def test_idle_clock_handles_millis_wrap(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        f"time 4294960000 {NOW}",
        "mode 0 1",
        "advance 89999 89",
        "pump_state 0",
        "advance 1 1",
        "pump_state 0",
    )
    assert rows == [[1, 0, 0], [0, 0, 0]]


def test_overdue_auto_runs_once_after_manual_inactivity(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        f"set 0 60 2 {NOW + 10}",
        "mode 0 1",
        "advance 90000 90",
        "status",
        "advance 2000 2",
        "status",
    )
    assert [row[0] for row in rows[1:]] == [1, 0]
    assert rows[-1][6] == NOW + 152


def test_cancelled_queue_retains_full_requested_time(core_binary: Path) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 1 1",
        "single 0 600",
        "duration_set 1 19",
        "single 1 19",
        "mode 1 0",
        "duration 1",
        "mode 1 1",
        "duration 1",
    )
    assert rows[-2:] == [[19], [19]]


@pytest.mark.parametrize("remaining", [1, 12, 59])
def test_repeated_resume_keeps_original_until_user_edits(core_binary: Path, remaining: int) -> None:
    rows = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "duration_set 0 60",
        "single 0 60",
        f"advance {(60 - remaining) * 1000} {60 - remaining}",
        "cancel 0",
        f"single 0 {remaining}",
        f"advance {remaining * 1000} {remaining}",
        "duration 0",
        "duration_set 0 9",
        "single 0 9",
        "advance 9000 9",
        "duration 0",
    )
    assert rows[-3:] == [[60], [0], [9]]
