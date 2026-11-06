#pragma once
#include <stdint.h>

struct PumpProgram {
  uint32_t pause;
  uint32_t run;
  uint32_t next;
};

bool scheduleBegin(bool reset);
bool scheduleTick();
bool scheduleDue(uint8_t pump);
uint32_t scheduleNow();
uint32_t scheduleNext(uint8_t pump);
const PumpProgram& scheduleProgram(uint8_t pump);
bool scheduleNeedsClock();
bool scheduleSetClock(uint32_t timestamp);
bool scheduleConfigureAt(uint8_t pump, uint32_t pause, uint32_t run, uint32_t first);
void scheduleStarted(uint8_t pump);
void scheduleStopped(uint8_t pump);
void scheduleInterrupted(uint8_t pump);
