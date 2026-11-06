#include <ui/lcd/manual_state.h>
#include <ui/lcd/i18n.h>
#include <core/pump_control.h>
#include <LCD_1602_RUS.h>

void manualUiRender() {
  if (!manualState.open || manualState.lcd == nullptr) return;
  bool freshFrame = manualState.dirty;
  const uint8_t pump = manualState.pump;
  const bool pending = pumpControlManualPending(pump);
  const bool waiting = pending && !pumpControlActive(pump);
  const uint32_t remaining = pumpControlManualRemaining(pump);
  if (manualState.screen == Screen::Pump &&
      (remaining != manualState.lastRemaining || pending != manualState.lastPending || waiting != manualState.lastWaiting)) {
    freshFrame = freshFrame || pending != manualState.lastPending || waiting != manualState.lastWaiting;
    manualState.dirty = true;
  }
  if (!manualState.dirty) return;
  if (freshFrame) uiBeginFrame(*manualState.lcd);
  if (manualState.screen == Screen::Selector) {
    uiTextRow(*manualState.lcd, 0, TR(MODE));
    uiTextRow(*manualState.lcd, 1, manualState.cursor == 0 ? TR(AUTO) : manualState.cursor == 1 ? TR(MANUAL) :
              manualState.cursor == 2 ? TR(CLOCK) : TR(CONCURRENCY), '>');
  } else if (manualState.screen == Screen::Concurrency) {
    uiFormatRow(*manualState.lcd, 0, TR(CONCURRENCY_VALUE), manualState.cursor == 0 ? '>' : ' ',
                unsigned(manualState.concurrencyDraft));
    uiActions(*manualState.lcd, 1, TR(SAVE), TR(CANCEL),
              manualState.cursor == 0 ? 255 : manualState.cursor - 1);
  } else {
    uiPumpRow(*manualState.lcd, 0, pump, manualState.cursor == 0 ? '>' : ' ');
    if (manualState.errorText) uiTextRow(*manualState.lcd, 1, manualState.errorText);
    else {
      const uint32_t duration = pending && !waiting ? remaining : pumpControlManualDuration(pump);
      uiFormatRow(*manualState.lcd, 1, TR(MANUAL_TIME),
                  manualState.cursor == 1 && !pending ? '>' : waiting ? '~' : ' ', uint16_t(duration / 3600),
                  manualState.cursor == 2 && !pending ? '>' : ':', uint8_t(duration % 3600 / 60),
                  manualState.cursor == 3 && !pending ? '>' : ':', uint8_t(duration % 60));
      uiActions(*manualState.lcd, 1, pending ? TR(STOP) : TR(START), nullptr, manualState.cursor == 4 ? 0 : 255, 9);
    }
  }
  manualState.lastRemaining = remaining;
  manualState.lastPending = pending;
  manualState.lastWaiting = waiting;
  manualState.dirty = false;
}
