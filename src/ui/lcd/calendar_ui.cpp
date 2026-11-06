#include <ui/lcd/calendar_ui.h>
#include <ui/lcd/i18n.h>
#include <LCD_1602_RUS.h>
#include <stdio.h>

void lcdRow(LCD_1602_RUS& lcd, uint8_t row, const char* text) {
  uiRow(lcd, row, text);
}
void calendarDraw(LCD_1602_RUS& lcd, const CalendarValue& v, uint8_t field,
                  bool clockMenu, bool canCancel) {
  uiBeginFrame(lcd);
  char row[17];
  snprintf(row, sizeof(row), " %02u.%02u.%04u", v.day, v.month, v.year);
  if (field < 3) row[field == 0 ? 0 : field == 1 ? 3 : 6] = '>';
  lcdRow(lcd, 0, row);
  uiFormatRow(lcd, 1, clockMenu ? PSTR("%c%02u%c%02u") : TR(START_TIME),
              field == 3 ? '>' : ' ', v.hour, field == 4 ? '>' : ':', v.minute);
  if (clockMenu)
    uiActions(lcd, 1, TR(CLOCK_SAVE), canCancel ? TR(BACK) : nullptr,
              field == 5 ? 0 : field == 6 ? 1 : 255, 6);
}
