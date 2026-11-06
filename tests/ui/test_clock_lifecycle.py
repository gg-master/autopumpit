"""Clock editor scenarios exercise the same application loop as firmware."""

import pytest

from tests.ui.test_lcd import UiRunner, build_ui, enter_manual


@pytest.fixture(scope="module")
def clock_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


def open_clock() -> list[str]:
    return ["event 4", "event 1", "event 1", "event 4"]


@pytest.mark.parametrize("language", [0, 1])
def test_clock_save_updates_rtc_and_resumes_due_automatic_program(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = ["save 0 60 5 1700000030", *open_clock(), "row"]
    commands += ["event 1"] * 4 + ["event 3", "row", "event 4", "event 4", "row"]
    commands += ["advance 5000", "row"]
    frames = runner.run(*commands)
    assert "2023" in frames[0].top
    assert "22>14" in frames[1].bottom
    assert [frame.mask for frame in frames] == [0, 0, 1, 0]
    assert frames[2].bottom.strip().endswith("22:15:05")


@pytest.mark.parametrize("language", [0, 1])
def test_clock_cancel_discards_draft_and_resumes_existing_schedule(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = ["save 0 100 10 1700000001", "advance 1000", "row", *open_clock(), "row"]
    commands += ["event 1"] * 4 + ["event 3", "event 1", "event 1", "row", "event 4", "row"]
    commands += ["advance 100000", "row", "advance 10000", "row"]
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [1, 0, 0, 0, 0, 1]
    assert ">" + runner.catalog.text("BACK") in frames[2].bottom
    assert frames[3].bottom.strip().endswith("22:15:11")


@pytest.mark.parametrize("language", [0, 1])
def test_opening_clock_cancels_active_and_queued_manual_requests(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = enter_manual() + ["event 1"] * 4 + ["event 4", "event 0", "event 3"]
    commands += [*enter_manual(), "event 1", "event 1", "event 1", "event 1", "event 4", "row"]
    commands += ["event 0", "event 4", "event 1", "event 4", "row"]
    commands += ["event 1"] * 6 + ["event 4", "row", "event 2", "row", "advance 5000", "row"]
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [1, 0, 0, 0, 0]
    assert frames[0].bottom.startswith("~00:00:05")
    assert runner.catalog.text("START") in frames[2].bottom
    assert runner.catalog.text("START") in frames[3].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_lost_rtc_requires_confirmation_and_offers_no_cancel(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = ["fault 1 1", "reboot", "row"] + ["event 1"] * 20 + ["row", "event 4", "row"]
    frames = runner.run(*commands)
    assert "2023" in frames[0].top
    assert ">" + runner.catalog.text("CLOCK_SAVE") in frames[1].bottom
    assert runner.catalog.text("BACK") not in frames[1].bottom
    assert frames[2].bottom.strip() == runner.catalog.text("DISABLED")
    assert [frame.mask for frame in frames] == [0, 0, 0]


@pytest.mark.parametrize("language", [0, 1])
def test_runtime_clock_fault_stays_latched_until_reboot(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = enter_manual() + ["event 1"] * 4 + ["event 4", "row"]
    commands += ["fault 0 0", "advance 300", "row", "fault 1 0", "advance 1000", "event 4", "row"]
    commands += ["reboot", "row"]
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [1, 0, 0, 0]
    assert frames[1].top.strip() == runner.catalog.text("RTC_ERROR")
    assert frames[2].top == frames[1].top
    assert frames[3].bottom.strip() == runner.catalog.text("DISABLED")


@pytest.mark.parametrize("language", [0, 1])
def test_clock_cancel_checks_rtc_before_admitting_overdue_program(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = ["save 0 60 5 1700000001", *open_clock(), "advance 2000", "fault 0 0"]
    commands += ["event 1"] * 6 + ["event 4", "row"]
    frame = runner.run(*commands)[0]
    assert frame.mask == 0
    assert frame.top.strip() == runner.catalog.text("RTC_ERROR")


@pytest.mark.parametrize("language", [0, 1])
def test_clock_cancel_reads_elapsed_rtc_time_before_resuming_schedule(
    clock_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = clock_runners[language]
    commands = ["save 0 60 5 1700000001", *open_clock(), "advance 2000"]
    commands += ["event 1"] * 6 + ["event 4", "row"]
    frame = runner.run(*commands)[0]
    assert frame.mask == 1
    assert frame.bottom.strip().endswith("22:14:27")
