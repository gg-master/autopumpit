"""Translation catalog boundary and display-budget regression tests."""

from pathlib import Path
from shutil import copyfile

import pytest

from tools.check_translations import TranslationError, check_translations

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalogs(tmp_path: Path) -> Path:
    source = ROOT / "config/locales"
    if not source.exists():
        source = ROOT / "include/i18n"
    for language in ("en", "ru"):
        _ = copyfile(source / f"{language}.h", tmp_path / f"{language}.h")
    return tmp_path


def test_accepts_repository_catalogs(catalogs: Path) -> None:
    # Given complete repository catalogs, when checked, then both pass.
    results = check_translations(catalogs, ROOT / "lib/LCD_1602_RUS/src/LCD_1602_RUS.cpp")
    assert [(result.language, result.keys) for result in results] == [("en", 41), ("ru", 41)]


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ('#define TXT_MODE "РЕЖИМ"', "", "keys"),
        ('"ПОМПА %u"', '"ПОМПА %s"', "placeholders"),
        ('"РЕЖИМ"', '"ABCDEFGHIJKLMNOPQ"', "row"),
        ('"ДАЛЕЕ"', '"ABCDEFGHIJKL"', "actions"),
        ('"РЕЖИМ"', '"🙂"', "characters"),
        ('"АКТИВНЫЕ ПОМПЫ"', '"БГДЖЗИЙЛ"', "cgram"),
        ('"ПОМПА %u"', '"ABCDEFGHIJKLMN%u"', "row"),
        (
            '#define TXT_CLOCK_SAVE "' + chr(1054) + chr(1050) + '"',
            '#define TXT_CLOCK_SAVE "SAVEEE"',
            "actions",
        ),
    ],
)
def test_rejects_invalid_translation(catalogs: Path, old: str, new: str, code: str) -> None:
    # Given one invalid translation mutation.
    target = catalogs / "ru.h"
    original = target.read_text(encoding="utf-8")
    assert old in original
    _ = target.write_text(original.replace(old, new), encoding="utf-8")
    # When checked, then the relevant constraint fails.
    with pytest.raises(TranslationError) as error:
        _ = check_translations(catalogs, ROOT / "lib/LCD_1602_RUS/src/LCD_1602_RUS.cpp")
    assert error.value.code == code


def test_accepts_crlf_catalogs(catalogs: Path) -> None:
    # Given Windows newlines.
    for target in catalogs.glob("*.h"):
        _ = target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    # When checked, then both catalogs pass.
    assert len(check_translations(catalogs, ROOT / "lib/LCD_1602_RUS/src/LCD_1602_RUS.cpp")) == 2
