"""Black-box scenarios drive the actual C++ firmware through fake hardware."""

import subprocess
from pathlib import Path
from typing import Final

import pytest

NOW: Final = 1_700_000_000


def run(core_binary: Path, *commands: str) -> list[list[int]]:
    """Run an isolated controller with deterministic clock and EEPROM."""
    result = subprocess.run(  # noqa: S603 - Runs only the fixture-built native harness.
        [str(core_binary)],
        input="\n".join(commands) + "\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    return [[int(value) for value in line.split()] for line in result.stdout.splitlines()]


def test_all_channels_run_sequentially_when_deadlines_tie(core_binary: Path) -> None:
    # Given all fourteen channels become due together.
    commands = ["boot 1", *(f"set {p} 100 1 {NOW + 1}" for p in range(14))]
    # When time reaches the common deadline and every one-second dose finishes.
    commands += ["advance 1000 1", "status"]
    for _ in range(13):
        commands += ["advance 1000 1", "status"]
    # Then ascending pump order breaks ties and no channels overlap.
    assert [state[0] for state in run(core_binary, *commands)[14:]] == [1 << p for p in range(14)]


def test_earliest_deadline_wins_when_channel_order_differs(core_binary: Path) -> None:
    # Given channel one has an earlier deadline than channel zero.
    # When both deadlines are overdue after an outage.
    states = run(
        core_binary,
        "boot 1",
        f"set 0 100 1 {NOW + 3}",
        f"set 1 100 1 {NOW + 1}",
        "advance 5000 5",
        "status",
    )
    # Then the earlier deadline wins.
    assert states[-1][0] == 2


@pytest.mark.parametrize(
    ("submission", "expected"),
    [
        ("single 0 5", 2),
        ("single 14 5", 2),
        ("mode 0 1\nsingle 0 0", 3),
        ("mode 0 1\nsingle 0 360000", 3),
        ("mode 0 1\nsingle 0 5\nsingle 0 5", 1),
        ("mode 0 1\nsingle 0 359999", 0),
    ],
)
def test_request_validation_when_input_is_invalid(
    core_binary: Path,
    submission: str,
    expected: int,
) -> None:
    # Given an enabled controller; when the request crosses its public boundary.
    results = run(core_binary, "boot 1", submission)
    # Then only Manual-mode channels and valid durations are accepted.
    assert results[-1] == [expected]


def test_busy_and_unavailable_when_controller_cannot_accept(core_binary: Path) -> None:
    # Given a running manual request; when another is submitted and power is stopped.
    results = run(
        core_binary, "boot 1", "mode 0 1", "single 0 1", "single 0 1", "off", "single 0 1"
    )
    # Then requests distinguish Busy from Unavailable.
    assert results == [[0], [1], [4]]


def test_manual_queue_uses_each_duration_when_clock_advances(core_binary: Path) -> None:
    # Given two manually selected channels have different durations.
    # When the first finishes and the second runs.
    results = run(
        core_binary,
        "boot 1",
        "mode 0 1",
        "mode 2 1",
        "single 0 2",
        "single 2 4",
        "status",
        "advance 2000 2",
        "status",
        "advance 3999 3",
        "status",
        "advance 1 1",
        "status",
    )
    # Then durations remain independent and all outputs stop on completion.
    assert [(row[0], row[3]) for row in results[2:]] == [(1, 2), (4, 4), (4, 1), (0, 0)]


@pytest.mark.parametrize("selected", [True, False])
def test_manual_handoff_when_automatic_channel_is_selected(
    core_binary: Path,
    *,
    selected: bool,
) -> None:
    # Given automatic channel zero is running.
    pump = 0 if selected else 1
    # When a manual request selects that channel or another channel.
    results = run(
        core_binary,
        "boot 1",
        f"set 0 100 2 {NOW + 1}",
        "advance 1000 1",
        f"mode {pump} 1",
        f"single {pump} 3",
        "status",
        "advance 2000 2",
        "status",
    )
    # Then a selected automatic dose stops immediately; an unselected one finishes.
    assert [row[0] for row in results[-2:]] == ([1, 1] if selected else [1, 2])


def test_millisecond_wrap_when_manual_dose_crosses_overflow(core_binary: Path) -> None:
    # Given a manual dose starts just before the 32-bit millisecond wrap.
    # When its full duration expires across wrap.
    results = run(
        core_binary,
        "boot 1",
        f"time 4294966796 {NOW}",
        "mode 0 1",
        "single 0 1",
        "advance 999 0",
        "status",
        "advance 1 1",
        "status",
    )
    # Then unsigned elapsed time still turns the relay off on time.
    assert [row[0] for row in results[-2:]] == [1, 0]


@pytest.mark.parametrize("fault", ["fault 0 0", "fault 1 1", f"time 300 {NOW - 1}"])
def test_fault_stops_outputs_when_clock_is_untrustworthy(core_binary: Path, fault: str) -> None:
    # Given an active manual dose; when clock connectivity, power, or monotonicity fails.
    results = run(
        core_binary, "boot 1", "mode 0 1", "single 0 100", fault, "advance 300 0", "status"
    )
    # Then the application safety cycle turns all relays off.
    assert results[-1][0] == 0


def test_clock_reset_when_time_is_lost(core_binary: Path) -> None:
    # Given the RTC lost power; when an invalid then valid clock is supplied.
    results = run(
        core_binary,
        "fault 1 1",
        "boot 1",
        "status",
        "clock 0",
        f"clock {NOW}",
        "boot 0",
        "mode 0 1",
        "single 0 1",
        "status",
    )
    # Then invalid time is rejected and a valid clock permits operation.
    assert results[0][5] == 1
    assert results[1:4] == [[0], [1], [0]]
    assert results[-1][0] == 1


def test_deadline_survives_reboot_when_dose_was_committed(core_binary: Path) -> None:
    # Given an automatic dose has started, committing the next deadline.
    # When power is lost mid-dose and the controller reboots.
    results = run(
        core_binary,
        "boot 1",
        f"set 0 100 10 {NOW + 1}",
        "advance 1000 1",
        "boot 0",
        "cycle",
        "status",
    )
    # Then the partial dose is not replayed and its stored deadline survives.
    assert results[-1][0] == 0
    assert results[-1][6] == NOW + 111


def test_active_low_relays_when_manual_queue_starts_and_stops(core_binary_low: Path) -> None:
    # Given an active-low hardware profile and all fourteen channels selected.
    commands = ["boot 1", *(f"mode {p} 1" for p in range(14))]
    commands += [*(f"single {p} 1" for p in range(14)), "status"]
    # When every dose expires in sequence.
    for _ in range(14):
        commands += ["advance 1000 1", "status"]
    # Then relay polarity is correct at every transition including all-off.
    assert [row[0] for row in run(core_binary_low, *commands)[14:]] == [
        *(1 << p for p in range(14)),
        0,
    ]
