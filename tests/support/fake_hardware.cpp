#include "fake_hardware.h"
#include <platform/ports.h>
#include <settings.h>
#include <core/pump_control.h>
#include <cstdlib>
namespace { std::array<bool, 32> configured{}; }
namespace testhardware {
std::array<uint8_t, 1024> memory;
std::array<bool, 32> pins{};
uint32_t ticks = 0, wall = 1700000000;
uint32_t activeTransitions = 0;
bool connected = true, lost = false;
int writesLeft = -1;
}
using namespace testhardware;
namespace hardware {
uint32_t milliseconds() { return ticks; }
void configureOutput(uint8_t pin) {
  if (!configured[pin] && pins[pin] == bool(SWITCH_LEVEL)) ++activeTransitions;
  configured[pin] = true;
}
void writeOutput(uint8_t pin, bool level) {
  const bool increasing = configured[pin] && pins[pin] != bool(SWITCH_LEVEL) && level == bool(SWITCH_LEVEL);
  pins[pin] = level;
  if (increasing) ++activeTransitions;
  uint16_t active = 0;
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p)
    if (configured[START_PIN + p] && pins[START_PIN + p] == bool(SWITCH_LEVEL)) ++active;
  if (increasing && active > pumpControlConcurrencyLimit()) std::abort();
}
bool clockBegin() { return connected; }
bool clockLostPower() { return lost; }
bool clockRead(uint32_t& timestamp) {
  timestamp = wall;
  return connected && !lost;
}
void clockAdjust(uint32_t timestamp) { wall = timestamp; lost = false; }
void storageRead(uint16_t address, uint8_t* data, uint16_t count) {
  for (unsigned i = 0; i < count; ++i) data[i] = memory[address + i];
}
void storageWrite(uint16_t address, uint8_t value) {
  if (writesLeft == 0) throw PowerCut{};
  if (writesLeft > 0) --writesLeft;
  memory[address] = value;
}
void storageFlush() {}
}
