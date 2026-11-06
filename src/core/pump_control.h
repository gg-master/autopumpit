#pragma once
#include <stdint.h>

enum class ManualRequestResult : uint8_t {
  Started,
  Busy,
  InvalidSelection,
  InvalidDuration,
  Unavailable,
};

void pumpControlBegin();
void pumpControlEnable();
bool pumpControlBusy(uint8_t pump);
void pumpControlExpire();
void pumpControlAutoStart();
void pumpControlStopAll();
void pumpControlResetPumpRuntime(uint8_t pump);
bool pumpControlManualMode(uint8_t pump);
void pumpControlSetManualMode(uint8_t pump, bool manual);
ManualRequestResult pumpControlStartManual(uint8_t pump, uint32_t seconds);
void pumpControlStopManualPump(uint8_t pump);
bool pumpControlManualPending(uint8_t pump);
uint32_t pumpControlManualRemaining(uint8_t pump);
void pumpControlTouchManual(uint8_t pump);
void pumpControlSetManualDuration(uint8_t pump, uint32_t seconds);
uint32_t pumpControlManualDuration(uint8_t pump);
uint8_t pumpControlConcurrencyLimit();
bool pumpControlSetConcurrencyLimit(uint8_t limit);
bool pumpControlActive(uint8_t pump);
