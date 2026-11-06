#pragma once
#include <stdint.h>
enum class ProgramSaveResult : uint8_t { Saved, Busy, PastStart };
void programPrepare();
bool programResetRequired();
void programReset();
bool programLoad(bool reset);
void programEnable();
bool programSetClock(uint32_t timestamp);
uint32_t programPause(uint8_t pump);
uint32_t programRun(uint8_t pump);
ProgramSaveResult programConfigure(uint8_t pump, uint32_t pause, uint32_t run, uint32_t first);

void programResetPump(uint8_t pump);
