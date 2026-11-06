"""Global settings are siblings of Pumps; pump modes belong to their channel."""

import pytest

from tests.ui.test_lcd import UiRunner, active_text, build_ui, enter_manual


@pytest.fixture(scope="module")
def navigation_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


@pytest.mark.parametrize("language", [0, 1])
def test_home_pump_modes_and_home_preserve_selected_channel(
    navigation_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = navigation_runners[language]
    frames = runner.run(
        "row",
        "event 4",
        "row",
        "event 4",
        "event 3",
        "row",
        "event 4",
        "row",
        *(["event 1"] * 20),
        "row",
        "event 4",
        "row",
        *(["event 1"] * 3),
        "event 4",
        "row",
        "event 4",
        "event 4",
        "row",
        from_home=True,
    )
    text = runner.catalog.text
    assert frames[0].bottom.strip() == frames[6].bottom.strip() == "--"
    assert frames[1].top.strip() == frames[5].top.strip() == text("MENU")
    assert frames[1].bottom.strip() == frames[5].bottom.strip() == ">" + text("PUMPS")
    assert frames[2].top.strip() == frames[7].top.strip() == ">" + text("PUMP_NAME") % 2
    assert frames[3].top.strip() == frames[4].top.strip() == text("PUMP_NAME") % 2
    assert frames[3].bottom.strip() == ">" + text("AUTO")
    assert frames[4].bottom.strip() == ">" + text("BACK")
    assert all(frame.mask == 0 for frame in frames)


@pytest.mark.parametrize("language", [0, 1])
def test_manual_pump_and_mode_menu_retain_running_session(
    navigation_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = navigation_runners[language]
    frames = runner.run(
        *enter_manual(),
        *(["event 1"] * 4),
        "event 4",
        "advance 1000",
        *(["event 0"] * 4),
        "event 4",
        "row",
        "event 1",
        "event 4",
        "row",
        *(["event 1"] * 3),
        "event 4",
        "row",
        "event 4",
        "event 4",
        "row",
        "event 4",
        "row",
    )
    assert [frame.mask for frame in frames] == [1] * 5
    text = runner.catalog.text
    assert frames[0].top.strip() == frames[4].top.strip() == text("PUMP_NAME") % 1
    assert frames[0].bottom.strip() == frames[4].bottom.strip() == ">" + text("MANUAL")
    assert frames[1].top.strip() == text("MENU")
    assert frames[2].bottom.strip() == active_text(runner, 1, manual=True)
    assert "00:00:04" in frames[3].bottom
    assert text("STOP") in frames[3].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_global_settings_do_not_require_selecting_a_pump(
    navigation_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = navigation_runners[language]
    frames = runner.run(
        "event 4",
        "event 1",
        "event 4",
        "row",
        *(["event 1"] * 6),
        "event 4",
        "row",
        "event 1",
        "event 4",
        "row",
        "event 4",
        "event 4",
        "row",
        "event 1",
        "event 4",
        "row",
        from_home=True,
    )
    text = runner.catalog.text
    assert "2023" in frames[0].top
    assert frames[1].top.strip() == frames[3].top.strip() == text("MENU")
    assert frames[1].bottom.strip() == ">" + text("CLOCK")
    assert ": 01" in frames[2].top
    assert frames[3].bottom.strip() == ">" + text("CONCURRENCY")
    assert frames[4].bottom.strip() == "--"
    assert all(frame.mask == 0 for frame in frames)


@pytest.mark.parametrize("language", [0, 1])
def test_manual_mode_expiration_does_not_close_global_menu(
    navigation_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = navigation_runners[language]
    frame = runner.run(*enter_manual(), "event 4", "event 1", "event 4", "advance 90000", "row")[0]
    assert frame.top.strip() == runner.catalog.text("MENU")
    assert frame.bottom.strip() == ">" + runner.catalog.text("PUMPS")
