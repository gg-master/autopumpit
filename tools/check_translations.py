# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
# How to run: install uv from https://docs.astral.sh/uv/getting-started/installation/
# Run: uv run tools/check_translations.py
# Or: uv run python -m tools.check_translations
"""Check translation headers against the LCD's character and frame budgets."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, override

ROOT: Final = Path(__file__).resolve().parents[1]
EXPECTED_KEYS: Final = frozenset(
    [
        "ACTIVE",
        "ACTIVE_COUNT",
        "ACTIVE_AUTO",
        "ACTIVE_MANUAL",
        "MENU",
        "PUMPS",
        "MODE",
        "AUTO",
        "MANUAL",
        "CLOCK",
        "CONCURRENCY",
        "CONCURRENCY_VALUE",
        "NEXT",
        "BACK",
        "START",
        "STOP",
        "SAVE",
        "CANCEL",
        "CLOCK_SAVE",
        "DISABLED",
        "WAIT_AUTO",
        "DONE",
        "STOPPED",
        "SELECT_PUMP",
        "SET_DURATION",
        "MANUAL_BUSY",
        "UNAVAILABLE",
        "PUMP_BUSY",
        "START_PAST",
        "RTC_ERROR",
        "RTC_WIRING",
        "RESET",
        "PUMP_NAME",
        "PUMP_TIME",
        "SELECTED",
        "CONFIRM",
        "RUNNING",
        "PAUSE_TIME",
        "RUN_TIME",
        "START_TIME",
        "MANUAL_TIME",
    ]
)
PAIRS: Final = (
    ("NEXT", "BACK"),
    ("START", "BACK"),
    ("STOP", "BACK"),
    ("SAVE", "CANCEL"),
    ("CLOCK_SAVE", "BACK"),
)
FRAMES: Final = (
    *(("PUMP_NAME", key) for key in ("AUTO", "MANUAL", "BACK")),
    *(("MENU", key) for key in ("PUMPS", "CLOCK", "CONCURRENCY", "ACTIVE")),
    ("CONCURRENCY_VALUE", "SAVE", "CANCEL"),
    ("ACTIVE_COUNT", "ACTIVE_AUTO", "PUMP_NAME"),
    ("ACTIVE_COUNT", "ACTIVE_MANUAL", "PUMP_NAME"),
    *(
        (key, state)
        for key in ("PUMP_NAME", "NEXT", "BACK")
        for state in ("SELECTED", "SELECT_PUMP")
    ),
    ("PUMP_TIME", "SET_DURATION"),
    ("PUMP_TIME", "NEXT", "BACK"),
    ("CONFIRM", "START", "BACK"),
    *(
        (key, "START", "BACK")
        for key in ("MANUAL_BUSY", "SELECT_PUMP", "SET_DURATION", "UNAVAILABLE")
    ),
    *((key, "STOP", "BACK") for key in ("RUNNING", "WAIT_AUTO")),
    *((key, "BACK") for key in ("STOPPED", "DONE")),
    *(
        ("PUMP_NAME", key)
        for key in ("DISABLED", "PUMP_BUSY", "START_PAST", "PAUSE_TIME", "RUN_TIME")
    ),
    ("PUMP_NAME", "SAVE", "CANCEL"),
    ("PUMP_NAME", "MANUAL_TIME", "START"),
    ("PUMP_NAME", "MANUAL_TIME", "STOP"),
    ("PUMP_NAME", "SET_DURATION"),
    ("PUMP_NAME", "UNAVAILABLE"),
    ("START_TIME",),
    ("CLOCK_SAVE", "BACK"),
    ("RTC_ERROR", "RTC_WIRING"),
    ("RESET",),
)
ROW_CELLS: Final = 16
NAME_CELLS: Final = 15
BUFFER_BYTES: Final = 32
CGRAM_GLYPHS: Final = 7


@dataclass(frozen=True, slots=True)
class TranslationError(Exception):
    """A catalog constraint failure with a stable machine-readable code."""

    code: str
    context: str

    @override
    def __str__(self) -> str:
        """Describe the failed catalog constraint."""
        return f"{self.context}: {self.code} constraint failed"


@dataclass(frozen=True, slots=True)
class Entry:
    """One parsed text macro."""

    key: str
    text: str


@dataclass(frozen=True, slots=True)
class Catalog:
    """A parsed language header."""

    language: str
    entries: tuple[Entry, ...]

    def text(self, key: str) -> str:
        """Return a known catalog key."""
        return next(entry.text for entry in self.entries if entry.key == key)


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Summary of a successfully checked language."""

    language: str
    keys: int
    maximum_glyphs: int


def read_catalog(path: Path) -> Catalog:
    """Parse string macros, rejecting malformed and duplicate definitions."""
    entries: list[Entry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#define TXT_"):
            continue
        match = re.fullmatch(r'#define TXT_(\w+)\s+("(?:[^"\\]|\\.)*")\s*', line)
        if match is None:
            msg = "syntax"
            raise TranslationError(msg, str(path))
        key, literal = match.groups()
        body = literal[1:-1]
        if re.search(r'\\(?!["\\nrt])', body):
            msg = "syntax"
            raise TranslationError(msg, str(path))
        value = re.sub(
            r'\\(["\\nrt])',
            lambda token: {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}[token[1]],
            body,
        )
        if any(entry.key == key for entry in entries):
            msg = "duplicate"
            raise TranslationError(msg, f"{path}.{key}")
        entries.append(Entry(key, value))
    if frozenset(entry.key for entry in entries) != EXPECTED_KEYS:
        msg = "keys"
        raise TranslationError(msg, str(path))
    return Catalog(path.stem, tuple(entries))


def placeholders(text: str) -> tuple[str, ...]:
    """Extract printf tokens including unsupported tokens for exact comparison."""
    return tuple(re.findall(r"%[^%\s]*?[a-zA-Z%]", text))


def sample(text: str) -> str:
    """Render the maximum values used by the firmware's display formatting."""
    return re.sub(r"%0?\d*u", "99", text).replace("%c", ">").replace("%s", "99:59:59")


def check_actions(catalog: Catalog) -> None:
    """Check paired controls and the per-pump time/action row."""
    for first, second in PAIRS:
        offset = 6 if first == "CLOCK_SAVE" else 0
        if len(catalog.text(first) + catalog.text(second)) + 2 + offset > ROW_CELLS:
            msg = "actions"
            raise TranslationError(msg, f"{catalog.language}.{first}/{second}")
    for action in ("START", "STOP"):
        if len(catalog.text(action)) + 10 > ROW_CELLS:
            msg = "actions"
            raise TranslationError(msg, f"{catalog.language}.MANUAL_TIME/{action}")


def check_catalog(catalog: Catalog, english: Catalog, custom: frozenset[str]) -> CheckResult:
    """Check one parsed catalog against English placeholders and LCD budgets."""
    for entry in catalog.entries:
        context = f"{catalog.language}.{entry.key}"
        if placeholders(entry.text) != placeholders(english.text(entry.key)):
            msg = "placeholders"
            raise TranslationError(msg, context)
        if re.fullmatch(r"[\x20-\x7e\u0410-\u044f\u0401\u0451]*", entry.text) is None:
            msg = "characters"
            raise TranslationError(msg, context)
        rendered = sample(entry.text)
        if len(rendered) > (NAME_CELLS if entry.key == "PUMP_NAME" else ROW_CELLS):
            msg = "row"
            raise TranslationError(msg, context)
        if len(rendered.encode("utf-8")) > BUFFER_BYTES:
            msg = "buffer"
            raise TranslationError(msg, context)
    check_actions(catalog)
    maximum = 0
    for frame in FRAMES:
        glyphs = frozenset("".join(catalog.text(key) for key in frame)) & custom
        maximum = max(maximum, len(glyphs))
        if len(glyphs) > CGRAM_GLYPHS:
            msg = "cgram"
            raise TranslationError(msg, f"{catalog.language}.{','.join(frame)}")
    return CheckResult(catalog.language, len(catalog.entries), maximum)


def check_translations(catalog_dir: Path, font_path: Path) -> tuple[CheckResult, ...]:
    """Check English and Russian headers using the vendored LCD glyph table."""
    font_pattern = re.compile(r"case (\d+):[^\n]*\n\s*memcpy_PF")
    custom = frozenset(
        chr(int(token[1])) for token in font_pattern.finditer(font_path.read_text(encoding="utf-8"))
    )
    if not custom:
        msg = "font"
        raise TranslationError(msg, str(font_path))
    english = read_catalog(catalog_dir / "en.h")
    russian = read_catalog(catalog_dir / "ru.h")
    return tuple(check_catalog(catalog, english, custom) for catalog in (english, russian))


def main() -> int:
    """Run repository checks and return a portable process status."""
    try:
        results = check_translations(
            ROOT / "config/locales", ROOT / "lib/LCD_1602_RUS/src/LCD_1602_RUS.cpp"
        )
    except (TranslationError, OSError, UnicodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    for result in results:
        print(
            " ".join(
                (
                    f"PASS {result.language}: {result.keys} keys, 16-cell rows, placeholders,",
                    f"action widths, max {result.maximum_glyphs}/7 custom glyphs per frame",
                )
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
