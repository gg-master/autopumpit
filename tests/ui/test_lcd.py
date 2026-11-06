import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest

from tests.support.native import ROOT, compile_native
from tools.check_translations import Catalog, read_catalog

SOURCES: Final = (
    "src/core/calendar.cpp",
    "src/core/program_settings.cpp",
    "src/core/pump_control.cpp",
    "src/core/concurrency_settings.cpp",
    "src/core/application.cpp",
    "src/ui/lcd/application.cpp",
    "src/core/rtc_schedule.cpp",
    "src/ui/lcd/auto_editor.cpp",
    "src/ui/lcd/calendar_ui.cpp",
    "src/ui/lcd/i18n.cpp",
    "src/ui/lcd/manual_ui.cpp",
    "src/ui/lcd/manual_view.cpp",
    "tests/support/fake_hardware.cpp",
    "tests/ui/harness.cpp",
)


@dataclass(frozen=True, slots=True)
class Frame:
    top: str
    bottom: str
    mask: int


@dataclass(frozen=True, slots=True)
class UiRunner:
    binary: Path
    catalog: Catalog

    def run(self, *commands: str, from_home: bool = False) -> list[Frame]:
        if not from_home:
            commands = ("event 4", "event 4", *commands)
        result = subprocess.run(  # noqa: S603 - Runs the compiled project UI test runner.
            [str(self.binary)],
            input="\n".join(commands),
            encoding="utf-8",
            capture_output=True,
            check=True,
            timeout=10,
        )
        frames: list[Frame] = []
        for line in result.stdout.splitlines():
            top, bottom, mask = line.split("|")
            assert len(top) == len(bottom) == 16
            frames.append(Frame(top, bottom, int(mask)))
        return frames


def build_ui(
    factory: pytest.TempPathFactory, language: int, *, home_timeout: int | None = 0
) -> UiRunner:
    flags = (f"-DUI_LANGUAGE={language}",)
    if home_timeout is not None:
        flags += (f"-DUI_HOME_TIMEOUT_SEC={home_timeout}",)
    binary = compile_native(factory.mktemp("lcd"), SOURCES, flags)
    name = ("en", "ru")[language]
    return UiRunner(binary, read_catalog(ROOT / f"config/locales/{name}.h"))


@pytest.fixture(scope="module")
def ui_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


def open_menu() -> list[str]:
    return ["event 4", "event 1", "event 1", "event 4"]


def enter_manual() -> list[str]:
    return ["event 4", "event 1", "event 4"]


@pytest.mark.parametrize("language", [0, 1])
def test_manual_validation_and_natural_completion(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    text = runner.catalog.text
    commands = ["row", "event 4", "row", "event 1", "event 4", "row"]
    commands += ["event 1"] * 3 + ["event 2"] * 5 + ["event 4", "event 4", "row"]
    commands += ["event 0", "event 3", "event 4", "event 4", "row", "advance 1000", "row"]
    frames = runner.run(*commands)
    assert frames[0].bottom.strip() == text("DISABLED")
    assert frames[1].bottom.strip() == ">" + text("AUTO")
    assert frames[2].top.strip() == ">" + text("PUMP_NAME") % 1
    assert "00:00:05" in frames[2].bottom
    assert text("START") in frames[2].bottom
    assert frames[3].bottom.strip() == text("SET_DURATION")
    assert frames[4].mask == 1
    assert text("STOP") in frames[4].bottom
    assert frames[5].mask == 0
    assert "00:00:01" in frames[5].bottom
    assert text("START") in frames[5].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_individual_times_navigation_and_stop(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    text = runner.catalog.text
    commands = enter_manual() + ["event 1"] * 4 + ["event 4", "row"]
    commands += ["event 0"] * 4 + ["event 3", "row"]
    commands += enter_manual() + ["event 1"] * 3 + ["event 3", "event 4", "event 4", "row"]
    commands += ["event 0"] * 4 + ["event 2", "row", "event 3", "row"]
    commands += (
        ["advance 5000", "row"] + ["event 1"] * 4 + ["event 4", "row", "advance 10000", "row"]
    )
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [1, 1, 1, 1, 1, 2, 0, 0]
    assert frames[1].bottom.strip() == text("DISABLED")
    assert frames[2].bottom.startswith("~00:00:06")
    assert frames[3].top.strip() == ">" + text("PUMP_NAME") % 1
    assert frames[4].top.strip() == ">" + text("PUMP_NAME") % 2
    assert frames[5].bottom.startswith(" 00:00:06")
    assert text("STOP") in frames[5].bottom
    assert text("START") in frames[6].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_short_click_selects_modes_and_hold_resets_only_selected_pump(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    text = runner.catalog.text
    commands = enter_manual() + ["event 1"] * 4 + ["event 4"]
    commands += ["event 0"] * 4 + ["event 3"] + enter_manual()
    commands += ["event 1"] * 3 + ["event 3", "event 4", "event 4"]
    commands += ["event 0"] * 4 + ["event 5", "row", "event 4", "row", "event 0", "event 4", "row"]
    commands += ["advance 5000", "row"]
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [1, 1, 1, 0]
    assert "00:00:05" in frames[0].bottom
    assert text("START") in frames[0].bottom
    assert frames[1].bottom.strip() == ">" + text("MANUAL")
    assert frames[2].bottom.strip() == text("DISABLED")


@pytest.mark.parametrize("language", [0, 1])
def test_long_press_resets_auto_only_on_heading(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    frames = runner.run(
        "save 0 60 2 1700000037",
        "save 1 60 2 1700000047",
        "event 1",
        "event 5",
        "row",
        "event 0",
        "event 5",
        "row",
        "event 3",
        "row",
        "advance 50000",
        "row",
    )
    assert "2023" in frames[0].top
    assert frames[1].bottom.strip() == runner.catalog.text("DISABLED")
    assert frames[2].bottom.strip().endswith("22:14:07")
    assert frames[3].mask == 2


@pytest.mark.parametrize("language", [0, 1])
def test_next_deadline_seconds_and_calendar_year(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    due = 1_700_000_037
    frames = runner.run(f"save 0 60 2 {due}", "row", "event 1", "row", "draw_clock 5", "row")
    assert frames[0].bottom.strip() == datetime.fromtimestamp(due, UTC).strftime("%d.%m %H:%M:%S")
    assert "2023" in frames[1].top
    assert frames[2].bottom.count(">") == 1
    assert runner.catalog.text("CLOCK_SAVE") in frames[2].bottom


@pytest.mark.parametrize("language", [0, 1])
def test_auto_reset_stops_only_selected_active_pump(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    frames = runner.run(
        "save 0 60 20 1700000001",
        "save 1 60 20 1700000001",
        "advance 1000",
        "row",
        "event 5",
        "row",
        "event 3",
        "row",
    )
    assert [frame.mask for frame in frames] == [1, 2, 2]
    assert frames[1].bottom.strip() == runner.catalog.text("DISABLED")


@pytest.mark.parametrize("language", [0, 1])
def test_hold_on_active_manual_resets_time_and_starts_next_request(
    ui_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = ui_runners[language]
    commands = enter_manual() + ["event 1"] * 3 + ["event 3", "event 4", "event 4"]
    commands += ["event 0"] * 4 + ["event 3"] + enter_manual()
    commands += ["event 1"] * 4 + ["event 4"]
    commands += ["event 0"] * 4 + ["event 2", "event 5", "row", "event 3", "row"]
    frames = runner.run(*commands)
    assert [frame.mask for frame in frames] == [2, 2]
    assert "00:00:05" in frames[0].bottom
    assert runner.catalog.text("START") in frames[0].bottom
    assert runner.catalog.text("STOP") in frames[1].bottom


def active_text(runner: UiRunner, pump: int, *, manual: bool = False) -> str:
    prefix = runner.catalog.text("ACTIVE_MANUAL" if manual else "ACTIVE_AUTO")
    return (prefix + runner.catalog.text("PUMP_NAME") % pump)[:16]
