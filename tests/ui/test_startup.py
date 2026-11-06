"""Catch intermediate startup drawings, not just the final visible screen."""

import subprocess

import pytest

from tests.ui.test_lcd import UiRunner, build_ui


@pytest.fixture(scope="module")
def startup_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    return build_ui(tmp_path_factory, 0), build_ui(tmp_path_factory, 1)


def draws(runner: UiRunner, commands: list[str]) -> list[int]:
    result = subprocess.run(  # noqa: S603 - Real application compiled by the test fixture.
        [str(runner.binary)],
        input="\n".join(commands),
        encoding="utf-8",
        capture_output=True,
        check=True,
        timeout=10,
    )
    return [int(value) for value in result.stdout.splitlines()]


@pytest.mark.parametrize("language", [0, 1])
def test_boot_and_reboot_draw_only_the_home_screen(
    startup_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    assert draws(startup_runners[language], ["draw_count", "reboot", "draw_count"]) == [1, 2]


@pytest.mark.parametrize("language", [0, 1])
def test_confirming_required_clock_draws_home_without_intermediate_pump(
    startup_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    before, after = draws(
        startup_runners[language],
        [
            "fault 1 1",
            "reboot",
            *(["event 1"] * 5),
            "draw_count",
            "event 4",
            "draw_count",
        ],
    )
    assert after - before == 1
