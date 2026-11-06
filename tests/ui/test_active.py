"""Exercise the live active-pump overview through the real LCD application."""

import pytest

from tests.ui.test_lcd import UiRunner, active_text, build_ui, enter_manual, open_menu


@pytest.fixture(scope="module")
def active_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


def open_active() -> list[str]:
    return [*open_menu(), *(["event 1"] * 3), "event 4"]


@pytest.mark.parametrize("language", [0, 1])
def test_empty_overview_and_return_to_menu(
    active_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = active_runners[language]
    frames = runner.run(*open_active(), "row", "event 4", "row")
    assert frames[0].top.strip() == runner.catalog.text("ACTIVE_COUNT") % (0, 1, 1)
    assert frames[0].bottom.strip() == "--"
    assert frames[1].bottom.strip() == ">" + runner.catalog.text("PUMPS")


@pytest.mark.parametrize("language", [0, 1])
def test_overview_tracks_auto_expiration_and_excludes_waiting_pumps(
    active_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = active_runners[language]
    frames = runner.run(
        "save 0 60 2 1700000001",
        "save 1 60 2 1700000001",
        *open_active(),
        "advance 1000",
        "row",
        "advance 2000",
        "row",
        "advance 2000",
        "row",
    )
    assert [frame.mask for frame in frames] == [1, 2, 0]
    assert [frame.bottom.strip() for frame in frames] == [
        active_text(runner, 1),
        active_text(runner, 2),
        "--",
    ]


@pytest.mark.parametrize("language", [0, 1])
def test_overview_tracks_manual_completion(
    active_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = active_runners[language]
    frames = runner.run(
        *enter_manual(),
        *(["event 1"] * 4),
        "event 4",
        *(["event 0"] * 4),
        *open_active(),
        "row",
        "advance 5000",
        "row",
    )
    assert [frame.mask for frame in frames] == [1, 0]
    assert [frame.bottom.strip() for frame in frames] == [active_text(runner, 1, manual=True), "--"]


@pytest.mark.parametrize("language", [0, 1])
def test_all_fourteen_pumps_paginate_and_clamp_when_finished(
    active_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = active_runners[language]
    limit = [
        *open_menu(),
        "event 1",
        "event 1",
        "event 4",
        *(["event 3"] * 13),
        "event 4",
        "event 4",
        "event 1",
        "event 4",
    ]
    programs = [f"save {pump} 60 5 1700000001" for pump in range(14)]
    commands = [*programs, *limit, "advance 1000", "row"]
    for _ in range(14):
        commands += ["event 1", "row"]
    commands += ["event 0", "row", "advance 5000", "row"]
    frames = runner.run(*commands)
    assert [frame.bottom.strip() for frame in frames] == [
        *(active_text(runner, pump) for pump in range(1, 15)),
        active_text(runner, 14),
        active_text(runner, 13),
        "--",
    ]
    assert [frame.mask for frame in frames] == [16383] * 16 + [0]
    assert frames[-1].top.strip() == runner.catalog.text("ACTIVE_COUNT") % (0, 1, 1)


@pytest.mark.parametrize("language", [0, 1])
def test_manual_queue_advances_while_overview_stays_open_after_idle_timeout(
    active_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = active_runners[language]
    start = [*enter_manual(), *(["event 1"] * 4), "event 4"]
    heading = ["event 0"] * 4
    frames = runner.run(
        *start,
        *heading,
        "event 3",
        *start,
        *heading,
        *open_active(),
        "row",
        "advance 5000",
        "row",
        "advance 5000",
        "row",
        "advance 90000",
        "row",
    )
    assert [frame.mask for frame in frames] == [1, 2, 0, 0]
    assert [frame.bottom.strip() for frame in frames] == [
        active_text(runner, 1, manual=True),
        active_text(runner, 2, manual=True),
        "--",
        "--",
    ]
    assert frames[-1].top.strip() == runner.catalog.text("ACTIVE_COUNT") % (0, 1, 1)
