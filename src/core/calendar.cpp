#include <core/calendar.h>

namespace {
bool leapYear(uint16_t year) { return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0); }
uint8_t monthDays(uint16_t year, uint8_t month) {
  if (month == 2) return leapYear(year) ? 29 : 28;
  return month == 4 || month == 6 || month == 9 || month == 11 ? 30 : 31;
}
uint8_t changed(uint8_t value, int8_t step, uint8_t low, uint8_t high) {
  const int16_t next = int16_t(value) + step;
  return next < low ? low : next > high ? high : next;
}
}
CalendarValue calendarFrom(uint32_t timestamp) {
  uint32_t days = timestamp / 86400UL;
  uint16_t year = 1970;
  while (days >= uint16_t(leapYear(year) ? 366 : 365)) {
    days -= leapYear(year) ? 366 : 365;
    ++year;
  }
  uint8_t month = 1;
  while (days >= monthDays(year, month)) days -= monthDays(year, month++);
  return {year, month, uint8_t(days + 1), uint8_t(timestamp % 86400UL / 3600),
          uint8_t(timestamp % 3600UL / 60)};
}
uint32_t calendarTimestamp(const CalendarValue& v) {
  uint32_t days = 0;
  for (uint16_t year = 1970; year < v.year; ++year) days += leapYear(year) ? 366 : 365;
  for (uint8_t month = 1; month < v.month; ++month) days += monthDays(v.year, month);
  return (days + v.day - 1) * 86400UL + uint32_t(v.hour) * 3600UL + uint32_t(v.minute) * 60UL;
}
void calendarChange(CalendarValue& v, uint8_t field, int8_t step) {
  switch (field) {
    case 0: v.day = changed(v.day, step, 1, monthDays(v.year, v.month)); break;
    case 1: v.month = changed(v.month, step, 1, 12); break;
    case 2: v.year = 2000 + changed(v.year - 2000, step, 0, 99); break;
    case 3: v.hour = changed(v.hour, step, 0, 23); break;
    case 4: v.minute = changed(v.minute, step, 0, 59); break;
  }
  const uint8_t maximum = monthDays(v.year, v.month);
  if (v.day > maximum) v.day = maximum;
}
