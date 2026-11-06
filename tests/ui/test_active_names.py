"""Active overview uses localized modes and configured channel names."""

import pytest

from tests.support.native import ROOT, compile_native
from tests.ui.test_lcd import SOURCES, UiRunner
from tools.check_translations import read_catalog


@pytest.fixture(scope="module")
def named_runners(tmp_path_factory: pytest.TempPathFactory) -> tuple[UiRunner, UiRunner]:
    config = tmp_path_factory.mktemp("named-config")
    names = [
        "Огурцы",
        "Помидоры",
        "Very long channel name",
        *(f"Channel {p}" for p in range(4, 15)),
    ]
    header = (
        "#pragma once\n#define USE_CUSTOM_CHANNEL_NAMES 1\nstatic const wchar_t* relayNames[] = {\n"
    )
    header += ",\n".join(f'L"{name}"' for name in names) + "\n};\n"
    _ = (config / "channel_names.h").write_text(header, encoding="utf-8")
    runners: list[UiRunner] = []
    for language, name in enumerate(("en", "ru")):
        binary = compile_native(
            tmp_path_factory.mktemp("named-lcd"),
            SOURCES,
            ("-I", str(config), f"-DUI_LANGUAGE={language}", "-DUI_HOME_TIMEOUT_SEC=0"),
        )
        runners.append(UiRunner(binary, read_catalog(ROOT / f"config/locales/{name}.h")))
    return runners[0], runners[1]


@pytest.mark.parametrize("language", [0, 1])
def test_custom_auto_and_manual_names_share_active_overview(
    named_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = named_runners[language]
    frames = runner.run(
        "capacity 2",
        "save 0 60 5 1700000001",
        "manual 1 10",
        "advance 1000",
        "row",
        "event 1",
        "row",
        from_home=True,
    )
    assert [frame.mask for frame in frames] == [3, 3]
    assert frames[0].bottom.strip() == runner.catalog.text("ACTIVE_AUTO") + "Огурцы"
    assert frames[1].bottom.strip() == runner.catalog.text("ACTIVE_MANUAL") + "Помидоры"
    assert frames[1].top.strip() == runner.catalog.text("ACTIVE_COUNT") % (2, 2, 2)


@pytest.mark.parametrize("language", [0, 1])
def test_custom_name_is_clipped_to_fourteen_cells_after_prefix(
    named_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = named_runners[language]
    frame = runner.run("manual 2 5", "row", from_home=True)[0]
    assert frame.bottom == runner.catalog.text("ACTIVE_MANUAL") + "Very long channel name"[:14]


@pytest.mark.parametrize("language", [0, 1])
def test_mode_change_refreshes_prefix_even_when_active_mask_is_unchanged(
    named_runners: tuple[UiRunner, UiRunner], language: int
) -> None:
    runner = named_runners[language]
    frames = runner.run(
        "save 0 60 5 1700000001", "advance 1000", "row", "manual 0 10", "row", from_home=True
    )
    assert [frame.mask for frame in frames] == [1, 1]
    assert [frame.bottom.strip() for frame in frames] == [
        runner.catalog.text("ACTIVE_AUTO") + "Огурцы",
        runner.catalog.text("ACTIVE_MANUAL") + "Огурцы",
    ]
