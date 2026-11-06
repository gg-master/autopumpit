import pytest

from tests.ui.test_lcd import UiRunner, build_ui, enter_manual


@pytest.fixture(scope="module")
def idle_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


@pytest.mark.parametrize("language", [0, 1])
def test_stopped_time_returns_after_automatic_idle_exit(
    idle_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = idle_runners[language]
    commands = enter_manual() + ["event 1"] * 4 + ["event 4", "advance 2000", "event 4", "row"]
    commands += ["advance 90000", "row", *enter_manual(), "row"]
    frames = runner.run(*commands)
    assert "00:00:03" in frames[0].bottom
    assert frames[1].bottom.strip() == runner.catalog.text("DISABLED")
    assert "00:00:03" in frames[2].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_finished_time_and_unselected_pump_idle_exit(
    idle_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = idle_runners[language]
    commands = enter_manual() + ["event 1"] * 4 + ["event 4", "advance 5000", "row"]
    commands += ["event 0"] * 4 + ["event 3", "advance 90000", "event 2", "row"]
    commands += [*enter_manual(), "row"]
    frames = runner.run(*commands)
    assert "00:00:05" in frames[0].bottom
    assert frames[1].bottom.strip() == runner.catalog.text("DISABLED")
    assert "00:00:05" in frames[2].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_editing_keeps_selected_manual_pump_alive(
    idle_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = idle_runners[language]
    frames = runner.run(
        *(
            [
                *enter_manual(),
                "advance 60000",
                "event 1",
                "event 3",
                "advance 60000",
                "row",
                "advance 30000",
                "row",
            ]
        )
    )
    assert "01:00:05" in frames[0].bottom
    assert frames[1].bottom.strip() == runner.catalog.text("DISABLED")


@pytest.mark.parametrize("language", [0, 1])
def test_auto_switch_snapshots_live_timer_then_full_completion_restores_initial(
    idle_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = idle_runners[language]
    commands = enter_manual() + ["event 1"] * 3 + ["event 3"] * 15
    commands += [
        "event 4",
        "event 4",
        "advance 7000",
        "event 0",
        "event 4",
        "event 0",
        "event 4",
        "row",
    ]
    commands += [*enter_manual(), "row"]
    commands += ["event 1"] * 4 + ["event 4", "advance 13000", "row", "advance 90000", "row"]
    commands += [*enter_manual(), "row"]
    frames = runner.run(*commands)
    assert frames[0].mask == 0
    assert "00:00:13" in frames[1].bottom
    assert "00:00:20" in frames[2].bottom
    assert frames[3].bottom.strip() == runner.catalog.text("DISABLED")
    assert "00:00:20" in frames[4].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_turn_at_field_boundary_does_not_replace_original_duration(
    idle_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = idle_runners[language]
    commands = enter_manual() + ["event 1"] * 3 + ["event 3"] * 15
    commands += ["event 4", "event 4", "advance 7000", "event 4"]
    commands += ["event 0"] * 3 + ["event 2"] + ["event 1"] * 3
    commands += ["event 4", "advance 13000", "row"]
    assert "00:00:20" in runner.run(*commands)[0].bottom
