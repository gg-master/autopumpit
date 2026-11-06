#include <core/calendar.h>
#include <iostream>
#include <string>
int main() {
  std::string command;
  while (std::cin >> command) {
    if (command == "from") {
      uint32_t timestamp; std::cin >> timestamp;
      const auto value = calendarFrom(timestamp);
      std::cout << value.year << ' ' << unsigned(value.month) << ' ' << unsigned(value.day)
                << ' ' << unsigned(value.hour) << ' ' << unsigned(value.minute) << '\n';
    } else {
      unsigned y, m, d, h, min; std::cin >> y >> m >> d >> h >> min;
      CalendarValue value{uint16_t(y), uint8_t(m), uint8_t(d), uint8_t(h), uint8_t(min)};
      if (command == "change") {
        unsigned field; int step; std::cin >> field >> step; calendarChange(value, field, step);
      }
      std::cout << calendarTimestamp(value) << '\n';
    }
  }
}
