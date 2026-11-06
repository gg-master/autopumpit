#pragma once
#include <array>
#include <stdint.h>
namespace testhardware {
extern std::array<uint8_t, 1024> memory;
extern std::array<bool, 32> pins;
extern uint32_t ticks, wall;
extern uint32_t activeTransitions;
extern bool connected, lost;
extern int writesLeft;
struct PowerCut {};
}
