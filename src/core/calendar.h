#pragma once
#include <stdint.h>
struct CalendarValue {
  uint16_t year;
  uint8_t month, day, hour, minute;
};
CalendarValue calendarFrom(uint32_t timestamp);
uint32_t calendarTimestamp(const CalendarValue& value);
void calendarChange(CalendarValue& value, uint8_t field, int8_t step);
