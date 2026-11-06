#include <core/pump_control.h>
#include <core/application.h>
#include <core/program_settings.h>
#include "../support/fake_hardware.h"
#include <core/rtc_schedule.h>
#include <platform/ports.h>
#include <settings.h>
#include <array>
#include <iostream>
#include <sstream>
#include <string>
using namespace testhardware;
namespace {
void boot(bool reset) { applicationBegin(reset); }
void cycle() { applicationTick(); }
void status() {
  uint16_t manualMask = 0;
  uint8_t activeManual = UINT8_MAX;
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p) {
    if (pumpControlManualPending(p)) manualMask |= uint16_t(1) << p;
    if (activeManual == UINT8_MAX && pumpControlManualMode(p) && pumpControlActive(p)) activeManual = p;
  }
  uint16_t mask = 0;
  for (unsigned p = 0; p < PUPM_AMOUNT; ++p)
    if (pins[START_PIN + p] == bool(SWITCH_LEVEL)) mask |= 1 << p;
  std::cout << mask << ' ' << bool(manualMask) << ' ' << manualMask << ' '
            << pumpControlManualRemaining(activeManual) << ' ' << unsigned(activeManual)
            << ' ' << scheduleNeedsClock();
  for (unsigned p = 0; p < PUPM_AMOUNT; ++p) std::cout << ' ' << scheduleNext(p);
  std::cout << '\n';
}
}
int main() {
  memory.fill(255);
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    std::string command;
    input >> command;
    try {
      if (command == "boot") { bool reset; input >> reset; boot(reset); }
      else if (command == "set") {
        unsigned p; uint32_t pause, run, first;
        input >> p >> pause >> run >> first;
        std::cout << scheduleConfigureAt(p, pause, run, first) << '\n';
      } else if (command == "advance") {
        uint32_t milliseconds, seconds;
        input >> milliseconds >> seconds; ticks += milliseconds; wall += seconds;
        cycle();
      } else if (command == "time") { input >> ticks >> wall; }
      else if (command == "transitions") std::cout << activeTransitions << '\n';
      else if (command == "cycle") cycle();
      else if (command == "limit") {
        unsigned limit; input >> limit; std::cout << pumpControlSetConcurrencyLimit(limit) << '\n';
      } else if (command == "limit_get") std::cout << unsigned(pumpControlConcurrencyLimit()) << '\n';
      else if (command == "mode") {
        unsigned pump; bool manual; input >> pump >> manual; pumpControlSetManualMode(pump, manual);
      } else if (command == "single") {
        unsigned pump; uint32_t seconds; input >> pump >> seconds;
        std::cout << unsigned(pumpControlStartManual(pump, seconds)) << '\n';
      } else if (command == "cancel") {
        unsigned pump; input >> pump; pumpControlStopManualPump(pump);
      } else if (command == "reset_pump") {
        unsigned pump; input >> pump; programResetPump(pump);
      } else if (command == "pump_state") {
        unsigned pump; input >> pump;
        std::cout << pumpControlManualMode(pump) << ' ' << pumpControlManualPending(pump)
                  << ' ' << pumpControlManualRemaining(pump) << '\n';
      } else if (command == "duration") {
        unsigned pump; input >> pump; std::cout << pumpControlManualDuration(pump) << '\n';
      } else if (command == "duration_set") {
        unsigned pump; uint32_t seconds; input >> pump >> seconds; pumpControlSetManualDuration(pump, seconds);
      } else if (command == "touch") {
        unsigned pump; input >> pump; pumpControlTouchManual(pump);
      } else if (command == "off") pumpControlStopAll();
      else if (command == "fault") input >> connected >> lost;
      else if (command == "clock") {
        uint32_t timestamp; input >> timestamp;
        std::cout << programSetClock(timestamp) << '\n';
      } else if (command == "cut") input >> writesLeft;
      else if (command == "corrupt") {
        unsigned address, value; input >> address >> value; memory[address] ^= value;
      } else if (command == "status") status();
      else if (command == "program_prepare") programPrepare();
      else if (command == "program_reset") programReset();
      else if (command == "program_load") {
        bool reset; input >> reset; std::cout << programLoad(reset) << '\n';
      } else if (command == "program_required") std::cout << programResetRequired() << '\n';
      else if (command == "program_enable") applicationResume();
      else if (command == "program_clock") {
        uint32_t timestamp; input >> timestamp; std::cout << programSetClock(timestamp) << '\n';
      } else if (command == "program_set") {
        unsigned pump; uint32_t pause, run, first; input >> pump >> pause >> run >> first;
        std::cout << unsigned(programConfigure(pump, pause, run, first)) << '\n';
      } else if (command == "program_values") {
        unsigned pump; input >> pump; std::cout << programPause(pump) << ' ' << programRun(pump) << '\n';
      } else if (command == "peek") {
        unsigned address; input >> address; std::cout << unsigned(memory[address]) << '\n';
      } else if (command == "poke") {
        unsigned address, value; input >> address >> value; memory[address] = value;
      }
      else return 2;
    } catch (const PowerCut&) { std::cout << "-1\n"; }
  }
}
