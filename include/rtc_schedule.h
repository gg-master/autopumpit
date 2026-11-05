#pragma once

#include <stdint.h>

bool scheduleBegin(bool reset, uint32_t* pauses, uint32_t* runs);
bool scheduleTick();
bool scheduleDue(uint8_t pump);
void scheduleConfigure(uint8_t pump, uint32_t pause, uint32_t run);
void scheduleStarted(uint8_t pump, uint32_t pause, uint32_t run);
void scheduleStopped(uint8_t pump, uint32_t pause, uint32_t run);
