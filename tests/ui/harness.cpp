#include <core/program_settings.h>
#include <core/pump_control.h>
#include <core/rtc_schedule.h>
#include <ui/lcd/application.h>
#include <ui/lcd/calendar_ui.h>
#include <settings.h>
#include <LCD_1602_RUS.h>
#include <fake_hardware.h>
#include <iostream>
#include <string>
using namespace testhardware;
int main() {
  memory.fill(255);
  LCD_1602_RUS lcd;
  lcdApplicationBegin(lcd, true, 1700000000);
  std::string command;
  while (std::cin >> command) {
    if (command == "event") {
      unsigned value; std::cin >> value;
      lcdApplicationTick(true, static_cast<ManualUiInput>(value));
    } else if (command == "interacting") {
      uint32_t delta; std::cin >> delta; ticks += delta; wall += delta / 1000;
      lcdApplicationTick(false, ManualUiInput::Click, true);
    } else if (command == "advance") {
      uint32_t delta; std::cin >> delta; ticks += delta; wall += delta / 1000;
      lcdApplicationTick();
    } else if (command == "draw_clock") {
      unsigned field; std::cin >> field;
      calendarDraw(lcd, calendarFrom(wall), field, true, true);
    } else if (command == "save") {
      unsigned pump; uint32_t pause, run, first; std::cin >> pump >> pause >> run >> first;
      programConfigure(pump, pause, run, first); lcdApplicationRefresh();
    } else if (command == "manual") {
      unsigned pump; uint32_t seconds; std::cin >> pump >> seconds;
      pumpControlSetManualMode(pump, true);
      pumpControlStartManual(pump, seconds);
      lcdApplicationTick();
    } else if (command == "capacity") {
      unsigned limit; std::cin >> limit;
      pumpControlSetConcurrencyLimit(limit);
      lcdApplicationTick();
    } else if (command == "reboot") {
      lcdApplicationBegin(lcd, false, 1700000000);
    } else if (command == "fault") {
      std::cin >> connected >> lost;
    } else if (command == "draw_count") {
      std::cout << lcd.topRowWrites() << '\n';
    } else if (command == "row") {
      uint16_t mask = 0;
      for (unsigned p = 0; p < PUPM_AMOUNT; ++p)
        if (pins[START_PIN + p] == bool(SWITCH_LEVEL)) mask |= 1 << p;
      std::cout << lcd.line(0) << '|' << lcd.line(1) << '|' << mask << '\n';
    } else return 2;
  }
}
