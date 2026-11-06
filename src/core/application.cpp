#include <core/application.h>
#include <core/program_settings.h>
#include <core/pump_control.h>
#include <core/rtc_schedule.h>
namespace {
ApplicationState state = ApplicationState::Running;
void clockFault() {
  pumpControlStopAll();
  state = ApplicationState::Fault;
}
}
ApplicationState applicationBegin(bool resetRequested) {
  programPrepare();
  const bool reset = resetRequested || programResetRequired();
  if (reset) programReset();
  if (!programLoad(reset)) clockFault();
  else if (scheduleNeedsClock()) state = ApplicationState::ClockRequired;
  else applicationResume();
  return state;
}
ApplicationState applicationState() { return state; }
void applicationResume() {
  programEnable();
  state = ApplicationState::Running;
}
void applicationTick(void (*handleInput)()) {
  if (state == ApplicationState::Fault) return;
  if (state == ApplicationState::Running) {
    if (!scheduleTick()) { clockFault(); return; }
    pumpControlExpire();
  }
  if (handleInput) handleInput();
  if (state == ApplicationState::Running) pumpControlAutoStart();
}
void applicationOpenClock() {
  if (state != ApplicationState::Running) return;
  pumpControlStopAll();
  state = ApplicationState::ClockEditing;
}
bool applicationSaveClock(uint32_t timestamp) {
  if (state != ApplicationState::ClockRequired && state != ApplicationState::ClockEditing) return false;
  if (!programSetClock(timestamp)) { clockFault(); return false; }
  applicationResume();
  return true;
}
bool applicationCancelClock() {
  if (state != ApplicationState::ClockEditing) return false;
  if (!scheduleTick()) { clockFault(); return false; }
  applicationResume();
  return true;
}
