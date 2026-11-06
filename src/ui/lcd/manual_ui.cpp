#include <ui/lcd/manual_state.h>
#include <ui/lcd/i18n.h>
#include <ui/lcd/manual_ui.h>
#include <core/pump_control.h>

ManualUiState manualState;
namespace {
void changeDuration(int8_t direction) {
  const uint32_t duration = pumpControlManualDuration(manualState.pump);
  uint8_t parts[] = {uint8_t(duration / 3600), uint8_t(duration % 3600 / 60), uint8_t(duration % 60)};
  const uint8_t field = manualState.cursor - 1;
  const int16_t next = int16_t(parts[field]) + direction;
  const uint8_t maximum = field == 0 ? 99 : 59;
  parts[field] = next < 0 ? 0 : next > maximum ? maximum : next;
  const uint32_t nextDuration = uint32_t(parts[0]) * 3600UL + uint32_t(parts[1]) * 60UL + parts[2];
  if (nextDuration != duration) pumpControlSetManualDuration(manualState.pump, nextDuration);
}
void startOrStop() {
  const uint8_t pump = manualState.pump;
  if (pumpControlManualPending(pump)) { pumpControlStopManualPump(pump); return; }
  switch (pumpControlStartManual(pump, pumpControlManualDuration(pump))) {
    case ManualRequestResult::Started: break;
    case ManualRequestResult::Busy: manualState.errorText = TR(MANUAL_BUSY); break;
    case ManualRequestResult::InvalidSelection: manualState.errorText = TR(SELECT_PUMP); break;
    case ManualRequestResult::InvalidDuration: manualState.errorText = TR(SET_DURATION); break;
    case ManualRequestResult::Unavailable: manualState.errorText = TR(UNAVAILABLE); break;
  }
}
}
void manualUiBegin(LCD_1602_RUS& display) {
  manualState.lcd = &display;
  manualState.open = false;
  manualState.dirty = false;

}
void manualUiOpen(uint8_t pump) {
  manualState.pump = pump;
  manualState.open = true;
  manualState.screen = Screen::Selector;
  manualState.manualAtOpen = pumpControlManualMode(pump);
  if (manualState.manualAtOpen) pumpControlTouchManual(pump);
  manualState.cursor = pumpControlManualMode(pump) ? 1 : 0;
  manualState.errorText = nullptr;
  manualState.dirty = true;
  manualUiRender();
}
void manualUiShowPump(uint8_t pump) {
  manualState.pump = pump;
  manualState.open = true;
  manualState.screen = Screen::Pump;
  pumpControlTouchManual(pump);
  manualState.cursor = 0;
  manualState.errorText = nullptr;
  manualState.dirty = true;
  manualUiRender();
}
void manualUiClose() { manualState.open = false; }
ManualUiAction manualUiHandle(ManualUiInput input) {
  if (!manualState.open) return ManualUiAction::None;
  const int8_t direction = input == ManualUiInput::TurnRight ? 1 : input == ManualUiInput::TurnLeft ? -1 : 0;
  const int8_t held = input == ManualUiInput::HeldTurnRight ? 1 : input == ManualUiInput::HeldTurnLeft ? -1 : 0;
  manualState.errorText = nullptr;
  if (pumpControlManualMode(manualState.pump) &&
      !(manualState.screen == Screen::Pump && held && manualState.cursor == 0))
    pumpControlTouchManual(manualState.pump);
  if (manualState.screen == Screen::Selector) {
    if (direction) {
      const int8_t next = manualState.cursor + direction;
      manualState.cursor = next < 0 ? 0 : next > 3 ? 3 : next;
    } else if (input == ManualUiInput::Click) {
      if (manualState.cursor == 2) { manualUiClose(); return ManualUiAction::SetClock; }
      if (manualState.cursor == 3) {
        manualState.screen = Screen::Concurrency;
        manualState.concurrencyDraft = pumpControlConcurrencyLimit();
        manualState.cursor = 0;
        manualState.dirty = true;
        manualUiRender();
        return ManualUiAction::None;
      }
      const bool manual = manualState.cursor == 1;
      pumpControlSetManualMode(manualState.pump, manual);
      if (!manual) { manualUiClose(); return ManualUiAction::ReturnToAuto; }
      manualUiShowPump(manualState.pump);
      return ManualUiAction::None;
    }
  } else if (manualState.screen == Screen::Concurrency) {
    if (direction) {
      const int8_t next = manualState.cursor + direction;
      manualState.cursor = next < 0 ? 0 : next > 2 ? 2 : next;
    } else if (held && manualState.cursor == 0) {
      const int8_t next = manualState.concurrencyDraft + held;
      manualState.concurrencyDraft = next < 1 ? 1 : next > PUPM_AMOUNT ? PUPM_AMOUNT : next;
    } else if (input == ManualUiInput::Click) {
      if (manualState.cursor == 0) manualState.cursor = 1;
      else {
        if (manualState.cursor == 1) pumpControlSetConcurrencyLimit(manualState.concurrencyDraft);
        manualUiOpen(manualState.pump);
        manualState.cursor = 3;
      }
    }
  } else {
    if (held && manualState.cursor == 0) {
      manualUiClose();
      return held > 0 ? ManualUiAction::NextPump : ManualUiAction::PreviousPump;
    }
    if (direction) {
      const int8_t next = manualState.cursor + direction;
      manualState.cursor = pumpControlManualPending(manualState.pump) ? (direction > 0 ? 4 : 0) :
          next < 0 ? 0 : next > 4 ? 4 : next;
    } else if (held && manualState.cursor < 4 && !pumpControlManualPending(manualState.pump)) {
      changeDuration(held);
    } else if (input == ManualUiInput::Hold && manualState.cursor == 0) {
      pumpControlStopManualPump(manualState.pump);
      pumpControlSetManualDuration(manualState.pump, 5);
    } else if (input == ManualUiInput::Click) {
      if (manualState.cursor == 0) { manualUiOpen(manualState.pump); return ManualUiAction::None; }
      if (manualState.cursor < 4) ++manualState.cursor;
      else startOrStop();
    }
  }
  manualState.dirty = true;
  manualUiRender();
  return ManualUiAction::None;
}
ManualUiAction manualUiRefresh() {
  if (manualState.open && manualState.screen != Screen::Concurrency &&
      (manualState.screen == Screen::Pump || manualState.manualAtOpen) &&
      !pumpControlManualMode(manualState.pump)) {
    manualUiClose();
    return ManualUiAction::ReturnToAuto;
  }
  manualUiRender();
  return ManualUiAction::None;
}
bool manualUiIsOpen() { return manualState.open; }
