#include <core/program_settings.h>
#include <core/pump_control.h>
#include <core/rtc_schedule.h>
#include <platform/ports.h>
#include <settings.h>

void programPrepare() { pumpControlBegin(); }
bool programResetRequired() {
  uint8_t marker;
  hardware::storageRead(1023, &marker, 1);
  return marker != 5;
}
void programReset() {
  hardware::storageWrite(1023, 0);
  pumpControlSetConcurrencyLimit(1);
}
bool programLoad(bool reset) { return scheduleBegin(reset); }
void programEnable() {
  hardware::storageWrite(1023, 5);
  pumpControlEnable();
}
bool programSetClock(uint32_t timestamp) { return scheduleSetClock(timestamp); }
uint32_t programPause(uint8_t pump) { return scheduleProgram(pump).pause; }
uint32_t programRun(uint8_t pump) { return scheduleProgram(pump).run; }
ProgramSaveResult programConfigure(uint8_t pump, uint32_t pause, uint32_t run, uint32_t first) {
  if (pump >= PUPM_AMOUNT) return ProgramSaveResult::PastStart;
  if (pumpControlBusy(pump)) return ProgramSaveResult::Busy;
  return scheduleConfigureAt(pump, pause, run, first) ? ProgramSaveResult::Saved : ProgramSaveResult::PastStart;
}
void programResetPump(uint8_t pump) {
  if (pump >= PUPM_AMOUNT) return;
  pumpControlResetPumpRuntime(pump);
  programConfigure(pump, 0, 0, 0);
}
