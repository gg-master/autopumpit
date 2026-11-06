#include <core/pump_control.h>
#include <core/concurrency_settings.h>
#include <core/rtc_schedule.h>
#include <platform/ports.h>
#include <settings.h>

static_assert(MANUAL_IDLE_TIMEOUT_SEC > 0 && MANUAL_IDLE_TIMEOUT_SEC <= UINT32_MAX / 1000UL,
              "Manual idle timeout must fit the millisecond clock");
namespace {
enum class PumpState : uint8_t { AutoIdle, AutoRunning, ManualIdle, ManualQueued, ManualRunning };
struct PumpRuntime {
  PumpState state = PumpState::AutoIdle;
  uint32_t stateSince = 0;
  uint32_t configuredSeconds = 5;
  uint32_t durationSeconds = 5;
};
PumpRuntime pumps[PUPM_AMOUNT];
bool enabled;
uint8_t queue[PUPM_AMOUNT];
uint8_t queueCount;

void writePump(uint8_t pump, bool on) {
  hardware::writeOutput(START_PIN + pump, on ? SWITCH_LEVEL : !SWITCH_LEVEL);
}
uint8_t activeCount() {
  uint8_t count = 0;
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p)
    if (pumpControlActive(p)) ++count;
  return count;
}
void removeQueued(uint8_t pump) {
  for (uint8_t i = 0; i < queueCount; ++i) {
    if (queue[i] != pump) continue;
    for (uint8_t j = i + 1; j < queueCount; ++j) queue[j - 1] = queue[j];
    --queueCount;
    return;
  }
}
void endManual(uint8_t pump, bool completed) {
  auto& runtime = pumps[pump];
  if (!pumpControlManualPending(pump)) return;
  const uint32_t remaining = runtime.state == PumpState::ManualRunning ?
      pumpControlManualRemaining(pump) : runtime.durationSeconds;
  if (runtime.state == PumpState::ManualRunning) writePump(pump, false);
  else removeQueued(pump);
  runtime.durationSeconds = completed || !remaining ? runtime.configuredSeconds : remaining;
  runtime.state = PumpState::ManualIdle;
  runtime.stateSince = hardware::milliseconds();
}
void startQueued() {
  while (queueCount && activeCount() < pumpControlConcurrencyLimit()) {
    const uint8_t pump = queue[0];
    removeQueued(pump);
    pumps[pump].state = PumpState::ManualRunning;
    pumps[pump].stateSince = hardware::milliseconds();
    writePump(pump, true);
  }
}
}

void pumpControlBegin() {
  enabled = false;
  queueCount = 0;
  concurrencySettingsBegin();
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p) {
    writePump(p, false);
    hardware::configureOutput(START_PIN + p);
    pumps[p] = PumpRuntime{};
  }
}
void pumpControlEnable() { enabled = true; }
uint8_t pumpControlConcurrencyLimit() { return concurrencySettingsLimit(); }
bool pumpControlSetConcurrencyLimit(uint8_t limit) { return concurrencySettingsSetLimit(limit); }
bool pumpControlActive(uint8_t pump) {
  return pump < PUPM_AMOUNT &&
      (pumps[pump].state == PumpState::AutoRunning || pumps[pump].state == PumpState::ManualRunning);
}
bool pumpControlManualMode(uint8_t pump) {
  if (pump >= PUPM_AMOUNT) return false;
  switch (pumps[pump].state) {
    case PumpState::AutoIdle:
    case PumpState::AutoRunning: return false;
    case PumpState::ManualIdle:
    case PumpState::ManualQueued:
    case PumpState::ManualRunning: return true;
  }
  return false;
}
bool pumpControlManualPending(uint8_t pump) {
  return pump < PUPM_AMOUNT &&
      (pumps[pump].state == PumpState::ManualQueued || pumps[pump].state == PumpState::ManualRunning);
}
bool pumpControlBusy(uint8_t pump) {
  return pumpControlActive(pump) || pumpControlManualPending(pump);
}
void pumpControlTouchManual(uint8_t pump) {
  if (pump < PUPM_AMOUNT && pumps[pump].state == PumpState::ManualIdle)
    pumps[pump].stateSince = hardware::milliseconds();
}
void pumpControlSetManualDuration(uint8_t pump, uint32_t seconds) {
  if (pump >= PUPM_AMOUNT || seconds > 359999UL || pumpControlManualPending(pump)) return;
  pumps[pump].configuredSeconds = pumps[pump].durationSeconds = seconds;
  pumpControlTouchManual(pump);
}
uint32_t pumpControlManualDuration(uint8_t pump) { return pumps[pump].durationSeconds; }
uint32_t pumpControlManualRemaining(uint8_t pump) {
  if (pump >= PUPM_AMOUNT || pumps[pump].state != PumpState::ManualRunning) return 0;
  const uint32_t elapsed = hardware::milliseconds() - pumps[pump].stateSince;
  const uint32_t duration = pumps[pump].durationSeconds * 1000UL;
  return elapsed >= duration ? 0 : (duration - elapsed + 999UL) / 1000UL;
}
void pumpControlStopManualPump(uint8_t pump) {
  if (pump < PUPM_AMOUNT) endManual(pump, false);
}
void pumpControlResetPumpRuntime(uint8_t pump) {
  if (pump >= PUPM_AMOUNT) return;
  endManual(pump, false);
  if (pumps[pump].state == PumpState::AutoRunning) writePump(pump, false);
  pumps[pump].state = PumpState::AutoIdle;
}
void pumpControlStopAll() {
  enabled = false;
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p) {
    endManual(p, false);
    if (pumps[p].state == PumpState::AutoRunning) {
      writePump(p, false);
      pumps[p].state = PumpState::AutoIdle;
    }
  }
}
void pumpControlSetManualMode(uint8_t pump, bool manual) {
  if (pump >= PUPM_AMOUNT) return;
  if (manual) {
    if (pumps[pump].state == PumpState::AutoRunning) {
      writePump(pump, false);
      scheduleInterrupted(pump);
    }
    if (!pumpControlManualMode(pump)) pumps[pump].state = PumpState::ManualIdle;
    pumpControlTouchManual(pump);
  } else if (pumpControlManualMode(pump)) {
    endManual(pump, false);
    pumps[pump].state = PumpState::AutoIdle;
  }
}
ManualRequestResult pumpControlStartManual(uint8_t pump, uint32_t seconds) {
  if (!enabled) return ManualRequestResult::Unavailable;
  if (pump >= PUPM_AMOUNT || !pumpControlManualMode(pump)) return ManualRequestResult::InvalidSelection;
  if (!seconds || seconds > 359999UL) return ManualRequestResult::InvalidDuration;
  if (pumpControlManualPending(pump)) return ManualRequestResult::Busy;
  if (pumps[pump].durationSeconds != seconds)
    pumps[pump].configuredSeconds = pumps[pump].durationSeconds = seconds;
  pumps[pump].state = PumpState::ManualQueued;
  queue[queueCount++] = pump;
  startQueued();
  return ManualRequestResult::Started;
}
void pumpControlExpire() {
  if (!enabled) return;
  const uint32_t now = hardware::milliseconds();
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p) {
    if (pumps[p].state == PumpState::AutoRunning) {
      const auto& program = scheduleProgram(p);
      if (program.pause && now - pumps[p].stateSince < program.run * 1000UL) continue;
      writePump(p, false);
      pumps[p].state = PumpState::AutoIdle;
      scheduleStopped(p);
    } else if (pumps[p].state == PumpState::ManualRunning &&
               now - pumps[p].stateSince >= pumps[p].durationSeconds * 1000UL) endManual(p, true);
  }
}
void pumpControlAutoStart() {
  if (!enabled) return;
  const uint32_t now = hardware::milliseconds();
  for (uint8_t p = 0; p < PUPM_AMOUNT; ++p)
    if (pumps[p].state == PumpState::ManualIdle &&
        now - pumps[p].stateSince >= MANUAL_IDLE_TIMEOUT_SEC * 1000UL)
      pumpControlSetManualMode(p, false);
  startQueued();
  while (activeCount() < pumpControlConcurrencyLimit()) {
    uint8_t selected = UINT8_MAX;
    for (uint8_t p = 0; p < PUPM_AMOUNT; ++p) {
      const auto& program = scheduleProgram(p);
      if (pumps[p].state != PumpState::AutoIdle || !program.pause || !program.run || !scheduleDue(p)) continue;
      if (selected == UINT8_MAX || scheduleNext(p) < scheduleNext(selected)) selected = p;
    }
    if (selected == UINT8_MAX) return;
    scheduleStarted(selected);
    pumps[selected].state = PumpState::AutoRunning;
    pumps[selected].stateSince = hardware::milliseconds();
    writePump(selected, true);
  }
}
