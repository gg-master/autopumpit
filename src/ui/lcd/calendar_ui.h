#pragma once
#include <core/calendar.h>
class LCD_1602_RUS;
void calendarDraw(LCD_1602_RUS& lcd, const CalendarValue& value, uint8_t field,
                  bool clockMenu = false, bool canCancel = false);
void lcdRow(LCD_1602_RUS& lcd, uint8_t row, const char* text);