import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.support.native import compile_native


@pytest.fixture(scope="module")
def calendar_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return compile_native(
        tmp_path_factory.mktemp("calendar"), ("src/core/calendar.cpp", "tests/calendar/harness.cpp")
    )


def rows(binary: Path, commands: list[str]) -> list[list[int]]:
    result = subprocess.run(  # noqa: S603 - Runs the repository-built test executable.
        [str(binary)],
        input="\n".join(commands),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return [[int(value) for value in row.split()] for row in result.stdout.splitlines()]


def test_all_months_roundtrip_against_python_datetime(calendar_binary: Path) -> None:
    dates = [
        datetime(year, month, 1, 23, 59, tzinfo=UTC)
        for year in range(2000, 2100)
        for month in range(1, 13)
    ]
    commands = [f"to {d.year} {d.month} {d.day} {d.hour} {d.minute}" for d in dates]
    assert rows(calendar_binary, commands) == [[int(d.timestamp())] for d in dates]
    commands = [f"from {int(d.timestamp())}" for d in dates]
    assert rows(calendar_binary, commands) == [
        [d.year, d.month, d.day, d.hour, d.minute] for d in dates
    ]


@pytest.mark.parametrize(
    ("value", "field", "step", "expected"),
    [
        ((2026, 1, 31, 0, 0), 1, 1, (2026, 2, 28, 0, 0)),
        ((2028, 2, 29, 0, 0), 2, -1, (2027, 2, 28, 0, 0)),
        ((2000, 2, 29, 0, 0), 2, -1, (2000, 2, 29, 0, 0)),
        ((2099, 12, 31, 23, 59), 2, 1, (2099, 12, 31, 23, 59)),
        ((2028, 2, 28, 23, 59), 0, 1, (2028, 2, 29, 23, 59)),
        ((2026, 2, 28, 0, 0), 0, 1, (2026, 2, 28, 0, 0)),
        ((2026, 1, 1, 0, 0), 3, -1, (2026, 1, 1, 0, 0)),
        ((2026, 1, 1, 23, 59), 4, 1, (2026, 1, 1, 23, 59)),
    ],
)
def test_calendar_edit_bounds(
    calendar_binary: Path, value: tuple[int, ...], field: int, step: int, expected: tuple[int, ...]
) -> None:
    command = "change " + " ".join(map(str, (*value, field, step)))
    assert rows(calendar_binary, [command]) == [[int(datetime(*expected, tzinfo=UTC).timestamp())]]
