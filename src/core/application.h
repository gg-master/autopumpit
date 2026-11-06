#pragma once
#include <stdint.h>
enum class ApplicationState : uint8_t { Running, ClockRequired, ClockEditing, Fault };
ApplicationState applicationBegin(bool resetRequested);
ApplicationState applicationState();
void applicationResume();
void applicationTick(void (*handleInput)() = nullptr);
void applicationOpenClock();
bool applicationSaveClock(uint32_t timestamp);
bool applicationCancelClock();
