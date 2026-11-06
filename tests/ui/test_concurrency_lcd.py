"""Runtime pump capacity through the real LCD input and rendering code."""

import pytest

from tests.ui.test_lcd import UiRunner, build_ui, enter_manual


@pytest.fixture(scope="module")
def capacity_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


def open_limit() -> list[str]:
    return ["event 4", "event 1", "event 1", "event 1", "event 4"]


@pytest.mark.parametrize("language", [0, 1])
def test_save_cancel_and_reboot(capacity_runners: tuple[UiRunner, UiRunner], language: int) -> None:
    runner = capacity_runners[language]
    commands = [*open_limit(), "row", "event 3", "row", "event 4", "row", "event 4"]
    commands += ["reboot", *open_limit(), "row"]
    commands += ["event 3", "event 1", "event 1", "row", "event 4", "reboot"]
    commands += [*open_limit(), "row"]
    frames = runner.run(*commands)
    assert frames[0].top == (runner.catalog.text("CONCURRENCY_VALUE") % (">", 1)).ljust(16)
    assert frames[1].top == (runner.catalog.text("CONCURRENCY_VALUE") % (">", 2)).ljust(16)
    assert frames[2].bottom.startswith(">" + runner.catalog.text("SAVE"))
    assert frames[3].top == frames[1].top
    assert ">" + runner.catalog.text("CANCEL") in frames[4].bottom
    assert frames[5].top == frames[1].top


@pytest.mark.parametrize("language", [0, 1])
def test_capacity_value_clamps_to_supported_channels(
    capacity_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    commands = open_limit() + ["event 2", "row"] + ["event 3"] * 20 + ["row"]
    frames = capacity_runners[language].run(*commands)
    assert ": 01" in frames[0].top
    assert ": 14" in frames[1].top


@pytest.mark.parametrize("language", [0, 1])
def test_parallel_manual_screens_show_each_running_timer(
    capacity_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = capacity_runners[language]
    commands = [*open_limit(), "event 3", "event 4", "event 4"]
    # Return from the settings item to Manual, then start pump1.
    commands += ["event 0", "event 0", "event 4"] + ["event 1"] * 4 + ["event 4"]
    commands += ["event 0", "event 3", *enter_manual()]
    commands += ["event 1"] * 3 + ["event 3", "event 4", "event 4", "row"]
    commands += ["advance 1000", "row", "event 0", "event 2", "row"]
    # Stop pump1 only; pump2 must keep running, with its own remainder.
    commands += ["event 1", "event 4", "row"] + ["event 0"] * 4
    commands += ["event 3", "row", "advance 5000", "row"]
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [3, 3, 3, 2, 2, 0]
    assert frames[0].bottom.startswith(" 00:00:06")
    assert frames[1].bottom.startswith(" 00:00:05")
    assert frames[2].bottom.startswith(" 00:00:04")
    assert frames[4].bottom.startswith(" 00:00:05")
    assert runner.catalog.text("STOP") in frames[4].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_raising_limit_from_manual_screen_starts_waiting_pump(
    capacity_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    commands = enter_manual() + ["event 1"] * 4 + ["event 4", "event 0", "event 3"]
    commands += [*enter_manual(), "event 1", "event 1", "event 1", "event 1", "event 4", "row"]
    commands += ["event 0", "event 4", "event 1", "event 1", "event 4", "row"]
    # Editing the draft must not start the waiting pump until Save.
    commands += ["event 3", "row", "event 4", "event 4", "row"]
    commands += ["event 0", "event 0", "event 4", "row", "advance 1000", "row"]
    frames = capacity_runners[language].run(*commands)
    assert [frame.mask for frame in frames] == [1, 1, 1, 3, 3, 3]
    assert frames[0].bottom.startswith("~00:00:05")
    assert frames[4].bottom.startswith(" 00:00:05")
    assert frames[5].bottom.startswith(" 00:00:04")
