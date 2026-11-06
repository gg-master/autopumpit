"""Concurrent admission and persistent capacity through the real controller."""

from pathlib import Path

import pytest

from tests.integration.test_core import NOW, run


def test_limit_defaults_to_one_and_rejects_invalid_values(core_binary: Path) -> None:
    # Given erased EEPROM; when valid and invalid limits cross the public boundary.
    results = run(core_binary, "boot 1", "limit_get", "limit 0", "limit 15", "limit_get")
    # Then invalid values cannot replace the safe default.
    assert results == [[1], [0], [0], [1]]


def test_two_manual_pumps_count_independently_and_admit_fifo(core_binary: Path) -> None:
    # Given two available slots and three manual requests in non-numeric order.
    commands = ["boot 1", "limit 2", "mode 7 1", "mode 2 1", "mode 4 1"]
    commands += ["single 7 2", "advance 1000 1", "single 2 4", "single 4 3", "status"]
    # When the first pump finishes, the queued pump starts its own complete dose.
    commands += ["advance 1000 1", "status", "pump_state 2", "pump_state 4"]
    commands += ["advance 3000 3", "status"]
    results = run(core_binary, *commands)
    # Then there are independent timers and no waiting time is charged.
    assert results[4][0] == (1 << 7) | (1 << 2)
    assert results[5][0] == (1 << 2) | (1 << 4)
    assert results[6:8] == [[1, 1, 3], [1, 1, 3]]
    assert results[8][0] == 0


def test_all_fourteen_automatic_pumps_can_run_at_once(core_binary: Path) -> None:
    # Given the maximum limit and fourteen programs sharing a deadline.
    commands = ["boot 1", "limit 14", *(f"set {p} 100 {p + 1} {NOW + 1}" for p in range(14))]
    # When each independently configured run expires.
    commands += ["advance 1000 1", "status"]
    for _ in range(14):
        commands += ["advance 1000 1", "status"]
    # Then every channel starts together and stops on its own duration.
    results = run(core_binary, *commands)
    assert [row[0] for row in results[15:]] == [16383 & ~((1 << p) - 1) for p in range(15)]


def test_manual_and_automatic_share_capacity_without_global_blocking(core_binary: Path) -> None:
    # Given an automatic pump is already running under a capacity of two.
    results = run(
        core_binary,
        "boot 1",
        "limit 2",
        f"set 0 100 10 {NOW + 1}",
        f"set 1 100 10 {NOW + 2}",
        "advance 1000 1",
        "mode 3 1",
        "single 3 2",
        "status",
        "advance 1000 1",
        "status",
        "advance 1000 1",
        "status",
    )
    # When a manual request fills the free slot and then finishes.
    # Then it coexists with Auto and the next overdue Auto fills the released slot.
    assert [results[i][0] for i in (4, 5, 6)] == [9, 9, 3]


def test_lower_limit_does_not_interrupt_but_prevents_new_admission(core_binary: Path) -> None:
    # Given three active pumps and a fourth waiting.
    commands = ["boot 1", "limit 3", *(f"mode {p} 1" for p in range(4))]
    commands += [*(f"single {p} {p + 1}" for p in range(4)), "limit 1", "status"]
    # When capacity is lowered and the active pumps finish independently.
    commands += ["advance 1000 1", "status", "advance 1000 1", "status", "advance 1000 1", "status"]
    results = run(core_binary, *commands)
    # Then excess active pumps finish; the queue waits until a new slot is available.
    assert [row[0] for row in results[6:]] == [7, 6, 4, 8]


def test_individual_stop_retains_other_timer_and_resumes_remaining(core_binary: Path) -> None:
    # Given concurrent manual pumps with different start times.
    results = run(
        core_binary,
        "boot 1",
        "limit 2",
        "mode 0 1",
        "mode 1 1",
        "single 0 20",
        "advance 7000 7",
        "single 1 9",
        "advance 1000 1",
        "cancel 0",
        "duration 0",
        "pump_state 1",
        "status",
        "mode 0 0",
        "mode 0 1",
        "duration 0",
    )
    # When one is stopped, only its remaining duration is retained.
    # Then the other pump continues with its own elapsed time.
    assert results[3:5] == [[12], [1, 1, 8]]
    assert results[5][0] == 2
    assert results[6] == [12]


def test_active_and_queued_pumps_are_exempt_from_idle_timeout(core_binary: Path) -> None:
    # Given two active long doses and a queued request.
    commands = ["boot 1", "limit 2", *(f"mode {p} 1" for p in range(3))]
    commands += ["single 0 400", "single 1 500", "single 2 10"]
    # When all have remained unattended longer than the idle timeout.
    commands += ["advance 301000 301", *(f"pump_state {p}" for p in range(3))]
    # Then active and waiting Manual modes remain intact.
    assert run(core_binary, *commands)[-3:] == [[1, 1, 99], [1, 1, 199], [1, 1, 0]]


def test_reboot_keeps_limit_but_never_resumes_manual_doses(core_binary: Path) -> None:
    # Given a saved capacity and two running manual requests.
    results = run(
        core_binary,
        "boot 1",
        "limit 2",
        "mode 0 1",
        "mode 1 1",
        "single 0 40",
        "single 1 50",
        "boot 0",
        "limit_get",
        "status",
        "pump_state 0",
    )
    # When power is restored, only the capacity setting persists.
    # Then manual output and mode are reset.
    assert results[-3] == [2]
    assert results[-2][0] == 0
    assert results[-1] == [0, 0, 0]


def test_clock_fault_stops_every_concurrent_output(core_binary: Path) -> None:
    # Given fourteen running doses; when the RTC becomes unavailable.
    commands = ["boot 1", "limit 14", *(f"mode {p} 1" for p in range(14))]
    commands += [*(f"single {p} 100" for p in range(14)), "fault 0 0", "advance 300 0", "status"]
    # Then all outputs stop, regardless of ownership or capacity.
    assert run(core_binary, *commands)[-1][0] == 0


@pytest.mark.parametrize("cut", range(9))
def test_torn_limit_save_keeps_previous_setting(core_binary: Path, cut: int) -> None:
    # Given capacity two has been durably saved.
    results = run(
        core_binary,
        "boot 1",
        "limit 2",
        f"cut {cut}",
        "limit 4",
        "cut -1",
        "boot 0",
        "limit_get",
    )
    # When each write of the replacement record loses power.
    # Then incomplete records cannot replace the previous complete setting.
    assert results[-1] == [2]


@pytest.mark.parametrize("byte", range(8))
def test_corrupt_latest_limit_record_falls_back(core_binary: Path, byte: int) -> None:
    # Given two persisted versions of capacity.
    results = run(
        core_binary,
        "boot 1",
        "limit 2",
        "limit 4",
        f"corrupt {640 + byte} 1",
        "boot 0",
        "limit_get",
    )
    # When any byte of the latest journal record is corrupted.
    # Then the earlier valid capacity is used.
    assert results[-1] == [2]


def test_factory_reset_restores_default_limit(core_binary: Path) -> None:
    # Given a persisted non-default limit; when all user settings are reset.
    results = run(
        core_binary,
        "program_prepare",
        "limit 7",
        "program_reset",
        "program_prepare",
        "limit_get",
    )
    # Then the reset value survives the next boot.
    assert results[-1] == [1]


def test_saving_same_limit_performs_no_eeprom_writes(core_binary: Path) -> None:
    # Given capacity two is saved and any further EEPROM write would fail.
    results = run(core_binary, "boot 1", "limit 2", "cut 0", "limit 2", "limit_get")
    # When the existing value is saved again, no write or power-cut exception occurs.
    assert results == [[1], [1], [2]]


def test_manual_queue_has_priority_over_overdue_auto(core_binary: Path) -> None:
    # Given two slots are occupied and an Auto program will become due.
    results = run(
        core_binary,
        "boot 1",
        "limit 2",
        f"set 0 100 20 {NOW + 1}",
        "mode 1 1",
        "mode 2 1",
        "mode 3 1",
        "single 1 1",
        "single 2 2",
        "single 3 3",
        "advance 1000 1",
        "status",
        "advance 1000 1",
        "status",
    )
    # When slots are released, queued Manual starts before overdue Auto.
    assert [results[i][0] for i in (5, 6)] == [12, 9]


def test_concurrent_active_low_outputs_and_millisecond_wrap(core_binary_low: Path) -> None:
    # Given active-low relays and manual doses starting just before uptime wraps.
    results = run(
        core_binary_low,
        "boot 1",
        "limit 2",
        f"time 4294966796 {NOW}",
        "mode 0 1",
        "mode 13 1",
        "single 0 1",
        "single 13 2",
        "status",
        "advance 1000 1",
        "status",
        "advance 1000 1",
        "status",
    )
    # When elapsed time crosses zero, both relays still stop on their own duration.
    assert [results[i][0] for i in (3, 4, 5)] == [8193, 8192, 0]
