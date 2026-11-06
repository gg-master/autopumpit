from pathlib import Path

import pytest

from tests.integration.test_core import NOW, run


def test_requests_follow_start_order_and_count_only_active_time(core_binary: Path) -> None:
    states = run(
        core_binary,
        "boot 1",
        "mode 13 1",
        "mode 2 1",
        "mode 8 1",
        "single 13 2",
        "single 2 3",
        "single 8 1",
        "status",
        "advance 1999 1",
        "pump_state 2",
        "status",
        "advance 1 1",
        "status",
        "advance 2999 2",
        "status",
        "advance 1 1",
        "status",
        "advance 1000 1",
        "status",
    )
    assert states[:3] == [[0], [0], [0]]
    assert states[4] == [1, 1, 0]
    assert [states[i][0] for i in (3, 5, 6, 7, 8, 9)] == [8192, 8192, 4, 4, 256, 0]
    assert states[6][3] == 3
    assert states[8][3] == 1


@pytest.mark.parametrize("cancelled", [0, 2])
def test_individual_stop_preserves_other_requests(core_binary: Path, cancelled: int) -> None:
    states = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 2 1",
        "mode 5 1",
        "single 0 2",
        "single 2 3",
        "single 5 1",
        f"cancel {cancelled}",
        "cycle",
        "status",
        f"pump_state {cancelled}",
        "advance 3000 3",
        "status",
    )
    assert states[3][0] == (4 if cancelled == 0 else 1)
    assert states[4] == [1, 0, 0]
    assert states[5][0] == 32


def test_mode_interrupts_own_auto_and_preserves_deadline_until_return(core_binary: Path) -> None:
    states = run(
        core_binary,
        "boot 1",
        f"set 0 100 20 {NOW + 1}",
        "advance 1000 1",
        "mode 0 1",
        "status",
        "advance 80000 80",
        "touch 0",
        "advance 80000 80",
        "touch 0",
        "advance 40000 40",
        "status",
        "mode 0 0",
        "cycle",
        "status",
    )
    assert states[1][0] == states[2][0] == 0
    assert states[1][6] == states[2][6] == NOW + 101
    assert states[3][0] == 1


def test_unselected_auto_finishes_before_manual_fifo(core_binary: Path) -> None:
    states = run(
        core_binary,
        "boot 1",
        f"set 0 100 5 {NOW + 1}",
        "advance 1000 1",
        "mode 3 1",
        "single 3 2",
        "pump_state 3",
        "status",
        "advance 5000 5",
        "status",
    )
    assert states[2] == [1, 1, 0]
    assert states[3][0] == 1
    assert states[4][0] == 8
    assert states[4][3] == 2


@pytest.mark.parametrize(
    ("submission", "expected"),
    [
        ("single 0 5", 2),
        ("single 14 5", 2),
        ("mode 0 1\nsingle 0 0", 3),
        ("mode 0 1\nsingle 0 360000", 3),
        ("off\nmode 0 1\nsingle 0 5", 4),
        ("mode 0 1\nsingle 0 359999", 0),
    ],
)
def test_single_request_validation(core_binary: Path, submission: str, expected: int) -> None:
    assert run(core_binary, "boot 1", submission)[-1] == [expected]


def test_duplicate_request_does_not_replace_running_duration(core_binary: Path) -> None:
    states = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "single 0 2",
        "single 0 8",
        "status",
        "advance 2000 2",
        "status",
        "pump_state 0",
        "single 0 3",
        "status",
    )
    assert states[:2] == [[0], [1]]
    assert states[2][3] == 2
    assert states[3][0] == 0
    assert states[4] == [1, 0, 0]
    assert states[-1][3] == 3


def test_fault_and_reboot_cancel_requests_and_restore_auto_mode(core_binary: Path) -> None:
    states = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 1 1",
        "single 0 3",
        "single 1 4",
        "fault 0 0",
        "advance 300 0",
        "status",
        "pump_state 1",
        "fault 1 0",
        "boot 0",
        "pump_state 0",
        "status",
    )
    assert states[2][0] == 0
    assert states[3] == [1, 0, 0]
    assert states[4] == [0, 0, 0]
    assert states[5][0] == 0


def test_fourteen_individual_requests_keep_fifo_order(core_binary: Path) -> None:
    commands = ["boot 1"] + [f"mode {pump} 1" for pump in range(14)]
    commands += [f"single {pump} 1" for pump in reversed(range(14))]
    commands += ["status"]
    for _ in range(13):
        commands += ["advance 1000 1", "status"]
    commands += ["advance 1000 1", "status"]
    results = run(core_binary, *commands)
    assert results[:14] == [[0]] * 14
    assert [row[0] for row in results[14:]] == [1 << pump for pump in reversed(range(14))] + [0]


def test_returning_auto_cancels_only_its_queued_request(core_binary: Path) -> None:
    results = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 1 1",
        "mode 2 1",
        "single 0 1",
        "single 1 5",
        "single 2 2",
        "mode 1 0",
        "pump_state 1",
        "advance 1000 1",
        "status",
    )
    assert results[3] == [0, 0, 0]
    assert results[4][0] == 4
    assert results[4][3] == 2


def test_idle_manual_mode_keeps_automatic_deadline(core_binary: Path) -> None:
    states = run(
        core_binary,
        "boot 1",
        f"set 0 60 5 {NOW + 10}",
        "mode 0 1",
        "single 0 2",
        "status",
        "advance 2000 2",
        "status",
        "mode 0 0",
        "cycle",
        "status",
    )
    assert [states[i][6] for i in (2, 3, 4)] == [NOW + 10] * 3
    assert [states[i][0] for i in (2, 3, 4)] == [1, 0, 0]


def test_auto_reset_is_persisted_and_keeps_other_channel_settings(core_binary: Path) -> None:
    states = run(
        core_binary,
        "program_prepare",
        "program_reset",
        "program_load 1",
        "program_enable",
        f"program_set 0 60 10 {NOW + 1}",
        f"program_set 1 70 10 {NOW + 1}",
        "advance 1000 1",
        "reset_pump 0",
        "cycle",
        "status",
        "program_values 0",
        "program_values 1",
        "program_prepare",
        "program_load 0",
        "program_values 0",
        "program_values 1",
        "status",
    )
    assert states[3][0] == 2
    assert states[4:6] == [[0, 0], [70, 10]]
    assert states[7:9] == [[0, 0], [70, 10]]
    assert states[-1][6] == 0
    assert states[-1][7] == NOW + 81
