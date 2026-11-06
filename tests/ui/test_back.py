"""Double-click returns to the parent screen without activating a menu action."""

import pytest

from tests.ui.test_clock_lifecycle import open_clock
from tests.ui.test_concurrency_lcd import open_limit
from tests.ui.test_lcd import UiRunner, build_ui, enter_manual


@pytest.fixture(scope="module")
def back_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


@pytest.mark.parametrize("language", [0, 1])
def test_home_ignores_back_and_menu_returns_home(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frames = runner.run("row", "event 6", "row", "event 4", "row", "event 6", "row", from_home=True)
    assert frames[0] == frames[1] == frames[3]
    assert frames[2].top.strip() == runner.catalog.text("MENU")


@pytest.mark.parametrize("language", [0, 1])
def test_pump_modes_return_to_same_pump_then_global_menu(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frames = runner.run("event 3", "row", "event 4", "event 1", "event 6", "row", "event 6", "row")
    assert frames[0] == frames[1]
    assert frames[1].top.strip() == ">" + runner.catalog.text("PUMP_NAME") % 2
    assert frames[2].top.strip() == runner.catalog.text("MENU")
    assert all(frame.mask == 0 for frame in frames)


@pytest.mark.parametrize("language", [0, 1])
def test_running_manual_back_preserves_timer_and_mode(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frames = runner.run(
        *enter_manual(),
        *(["event 1"] * 4),
        "event 4",
        "advance 1000",
        "event 6",
        "row",
        "event 4",
        "row",
        "event 4",
        "row",
        "event 6",
        "row",
    )
    assert [frame.mask for frame in frames] == [1] * 4
    assert frames[0].top.strip() == runner.catalog.text("MENU")
    assert "00:00:04" in frames[1].bottom
    assert frames[2].bottom.strip() == ">" + runner.catalog.text("MANUAL")
    assert frames[1] == frames[3]


@pytest.mark.parametrize("language", [0, 1])
def test_back_discards_auto_draft(back_runners: tuple[UiRunner, UiRunner], language: int) -> None:
    runner = back_runners[language]
    frames = runner.run(
        "save 0 60 2 1700001000",
        *(["event 1"] * 9),
        "event 3",
        "event 6",
        "row",
        "event 4",
        *(["event 1"] * 9),
        "row",
    )
    assert frames[0].top.strip() == runner.catalog.text("MENU")
    assert ">00:00:02" in frames[1].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_back_discards_limit_draft_and_keeps_menu_context(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frames = runner.run(*open_limit(), "event 3", "event 6", "row", "event 4", "row")
    assert frames[0].top.strip() == runner.catalog.text("MENU")
    assert frames[0].bottom.strip() == ">" + runner.catalog.text("CONCURRENCY")
    assert ": 01" in frames[1].top


@pytest.mark.parametrize("language", [0, 1])
def test_back_cancels_clock_draft_and_resumes_due_program(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frames = runner.run(
        "save 0 60 5 1700000001",
        *open_clock(),
        "row",
        "event 3",
        "advance 2000",
        "event 6",
        "row",
        "event 4",
        "row",
    )
    assert [frame.mask for frame in frames] == [0, 1, 0]
    assert frames[1].top.strip() == runner.catalog.text("MENU")
    assert frames[1].bottom.strip() == ">" + runner.catalog.text("CLOCK")
    assert frames[0].top == frames[2].top


@pytest.mark.parametrize("language", [0, 1])
def test_back_does_not_cancel_required_clock_or_hide_fault(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frames = runner.run(
        "fault 1 1",
        "reboot",
        "row",
        "event 6",
        "row",
        "fault 0 0",
        "reboot",
        "row",
        "event 6",
        "row",
        from_home=True,
    )
    assert frames[0] == frames[1]
    assert "2023" in frames[0].top
    assert frames[2] == frames[3]
    assert frames[2].top.strip() == runner.catalog.text("RTC_ERROR")


@pytest.mark.parametrize("language", [0, 1])
def test_back_from_clock_revalidates_rtc_before_resuming(
    back_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = back_runners[language]
    frame = runner.run(*open_clock(), "fault 0 0", "advance 300", "event 6", "row")[0]
    assert frame.mask == 0
    assert frame.top.strip() == runner.catalog.text("RTC_ERROR")
