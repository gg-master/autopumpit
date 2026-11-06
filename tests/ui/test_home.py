"""Home screen lifecycle through the actual application and LCD renderer."""

import pytest

from tests.ui.test_clock_lifecycle import open_clock
from tests.ui.test_concurrency_lcd import open_limit
from tests.ui.test_lcd import UiRunner, active_text, build_ui, enter_manual


@pytest.fixture(scope="module")
def home_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return (
        build_ui(tmp_path_factory, 0, home_timeout=None),
        build_ui(tmp_path_factory, 1, home_timeout=None),
    )


@pytest.mark.parametrize("language", [0, 1])
def test_boot_reboot_and_click_to_program(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run("row", "event 4", "row", "event 4", "row", "reboot", "row", from_home=True)
    assert frames[0].bottom.strip() == frames[3].bottom.strip() == "--"
    assert frames[1].bottom.strip() == ">" + runner.catalog.text("PUMPS")
    assert frames[2].bottom.strip() == runner.catalog.text("DISABLED")


@pytest.mark.parametrize("language", [0, 1])
def test_timeout_boundary_and_input_restarts_timer(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        "advance 29000", "row", "event 4", "advance 29000", "row", "advance 1000", "row"
    )
    assert frames[0].bottom.strip() == runner.catalog.text("DISABLED")
    assert frames[1].bottom.strip() == ">" + runner.catalog.text("AUTO")
    assert frames[2].bottom.strip() == "--"


@pytest.mark.parametrize("language", [0, 1])
def test_return_home_keeps_manual_pump_running(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        *enter_manual(),
        "event 1",
        "event 3",
        "event 1",
        "event 1",
        "event 1",
        "event 4",
        "row",
        "advance 30000",
        "row",
    )
    assert [frame.mask for frame in frames] == [1, 1]
    assert frames[1].bottom.strip() == active_text(runner, 1, manual=True)


@pytest.mark.parametrize("language", [0, 1])
def test_timeout_discards_auto_draft(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        "save 0 60 2 1700001000",
        *(["event 1"] * 9),
        "event 3",
        "advance 30000",
        "row",
        "event 4",
        "event 4",
        *(["event 1"] * 9),
        "row",
    )
    assert frames[0].bottom.strip() == "--"
    assert ">00:00:02" in frames[1].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_timeout_discards_concurrency_draft(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        *open_limit(),
        "event 3",
        "advance 30000",
        "row",
        "event 4",
        "event 1",
        "event 1",
        "event 4",
        "row",
    )
    assert frames[0].bottom.strip() == "--"
    assert ": 01" in frames[1].top


@pytest.mark.parametrize("language", [0, 1])
def test_clock_timeout_cancels_draft_and_resumes_program(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        "save 0 60 60 1700000001",
        *open_clock(),
        "event 3",
        "advance 30000",
        "row",
        "event 4",
        "event 1",
        "event 4",
        "row",
    )
    assert frames[0].mask == 1
    assert frames[0].bottom.strip() == active_text(runner, 1)
    assert "2023" in frames[1].top


@pytest.mark.parametrize("language", [0, 1])
def test_required_clock_and_fault_are_not_hidden_by_timeout(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        "fault 1 1",
        "reboot",
        "advance 60000",
        "row",
        "fault 0 0",
        "reboot",
        "advance 60000",
        "row",
        from_home=True,
    )
    assert "2023" in frames[0].top
    assert frames[1].top.strip() == runner.catalog.text("RTC_ERROR")


@pytest.mark.parametrize("language", [0, 1])
def test_home_updates_without_input_and_preserves_selected_pump(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        "save 0 60 60 1700000001",
        "advance 1000",
        "row",
        "event 4",
        "event 4",
        "event 3",
        "advance 30000",
        "row",
        "event 4",
        "event 4",
        "row",
        from_home=True,
    )
    assert frames[0].bottom.strip() == frames[1].bottom.strip() == active_text(runner, 1)
    assert frames[2].top.strip() == ">" + runner.catalog.text("PUMP_NAME") % 2


@pytest.mark.parametrize("language", [0, 1])
def test_idle_timer_handles_millis_wrap_and_reboot_resets_timer(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run(
        "advance 4294960000",
        "event 4",
        "advance 29999",
        "row",
        "advance 1",
        "row",
        "reboot",
        "event 4",
        "advance 29999",
        "row",
        "advance 1",
        "row",
        from_home=True,
    )
    assert frames[0].bottom.strip() == ">" + runner.catalog.text("PUMPS")
    assert frames[1].bottom.strip() == frames[3].bottom.strip() == "--"
    assert frames[2].bottom.strip() == ">" + runner.catalog.text("PUMPS")


@pytest.mark.parametrize("language", [0, 1])
def test_clock_timeout_validates_rtc_before_resuming(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frame = runner.run(*open_clock(), "fault 0 0", "advance 30000", "row")[0]
    assert frame.mask == 0
    assert frame.top.strip() == runner.catalog.text("RTC_ERROR")


def test_zero_timeout_disables_idle_return(tmp_path_factory: pytest.TempPathFactory) -> None:
    runner = build_ui(tmp_path_factory, 0, home_timeout=0)
    frame = runner.run("advance 60000", "row")[0]
    assert frame.bottom.strip() == runner.catalog.text("DISABLED")


@pytest.mark.parametrize("language", [0, 1])
def test_pending_gesture_keeps_screen_until_click_is_classified(
    home_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = home_runners[language]
    frames = runner.run("advance 29900", "interacting 200", "row", "event 4", "row")
    assert frames[0].bottom.strip() == runner.catalog.text("DISABLED")
    assert frames[1].bottom.strip() == ">" + runner.catalog.text("AUTO")
