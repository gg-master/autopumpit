#include <ui/lcd/i18n.h>
#include <channel_names.h>
#include <LCD_1602_RUS.h>
#include <stdarg.h>
#include <stdio.h>

namespace {
uint8_t printCells(LCD_1602_RUS& lcd, const char* text, uint8_t limit) {
  uint8_t cells = 0;
  while (*text && cells < limit) {
    char token[3] = {*text++, 0, 0};
    if ((uint8_t(token[0]) & 0xe0) == 0xc0 && (uint8_t(*text) & 0xc0) == 0x80)
      token[1] = *text++;
    lcd.print(token);
    ++cells;
  }
  return cells;
}
uint8_t flashCells(PGM_P text) {
  uint8_t count = 0;
  if (text == nullptr) return 0;
  for (uint8_t c; (c = pgm_read_byte(text++)) != 0;)
    if ((c & 0xc0) != 0x80) ++count;
  return count;
}
uint8_t printFlash(LCD_1602_RUS& lcd, PGM_P text, uint8_t limit) {
  char buffer[33];
  strncpy_P(buffer, text, sizeof(buffer) - 1);
  buffer[sizeof(buffer) - 1] = 0;
  return printCells(lcd, buffer, limit);
}
void pad(LCD_1602_RUS& lcd, uint8_t cells) {
  while (cells++ < 16) lcd.print(' ');
}
}

void uiBeginFrame(LCD_1602_RUS& lcd) {
#if UI_LANGUAGE == 1 || USE_CUSTOM_CHANNEL_NAMES
  // A new frame needs a fresh CGRAM cache; timed updates reuse the same glyphs.
  lcd.clear();
#else
  (void)lcd;
#endif
}
void uiRow(LCD_1602_RUS& lcd, uint8_t row, const char* text, char marker) {
  lcd.setCursor(0, row);
  if (marker) lcd.print(marker);
  const uint8_t prefix = marker ? 1 : 0;
  pad(lcd, prefix + printCells(lcd, text, 16 - prefix));
}
void uiTextRow(LCD_1602_RUS& lcd, uint8_t row, PGM_P text, char marker) {
  lcd.setCursor(0, row);
  if (marker) lcd.print(marker);
  const uint8_t prefix = marker ? 1 : 0;
  pad(lcd, prefix + printFlash(lcd, text, 16 - prefix));
}
void uiFormatRow(LCD_1602_RUS& lcd, uint8_t row, PGM_P format, ...) {
  char buffer[33];
  va_list args;
  va_start(args, format);
  vsnprintf_P(buffer, sizeof(buffer), format, args);
  va_end(args);
  uiRow(lcd, row, buffer);
}
void uiActions(LCD_1602_RUS& lcd, uint8_t row, PGM_P first, PGM_P second,
               uint8_t selected, uint8_t offset) {
  lcd.setCursor(offset, row);
  lcd.print(selected == 0 ? '>' : ' ');
  uint8_t secondSize = flashCells(second);
  if (secondSize > 14 - offset) secondSize = 14 - offset;
  const uint8_t split = second ? 15 - secondSize : 16;
  uint8_t cells = offset + 1 + printFlash(lcd, first, split - offset - 1);
  while (cells < split) { lcd.print(' '); ++cells; }
  if (second) {
    lcd.print(selected == 1 ? '>' : ' ');
    cells += 1 + printFlash(lcd, second, 15 - split);
  }
  pad(lcd, cells);
}
void uiPumpRow(LCD_1602_RUS& lcd, uint8_t row, uint8_t pump, char marker, PGM_P prefix) {
  lcd.setCursor(0, row);
  uint8_t cells = marker ? 1 : 0;
  if (marker) lcd.print(marker);
  if (prefix) cells += printFlash(lcd, prefix, 16 - cells);
#if USE_CUSTOM_CHANNEL_NAMES
  const wchar_t* name = relayNames[pump];
  while (*name && cells < 16) {
    const wchar_t token[2] = {*name++, 0};
    lcd.print(token);
    ++cells;
  }
#else
  char buffer[33];
  snprintf_P(buffer, sizeof(buffer), TR(PUMP_NAME), pump + 1);
  cells += printCells(lcd, buffer, 16 - cells);
#endif
  pad(lcd, cells);
}