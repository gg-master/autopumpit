#include <ui/lcd/application.h>
#include <ui/lcd/auto_editor.h>
#include <ui/lcd/calendar_ui.h>
#include <ui/lcd/i18n.h>
#include <core/application.h>
#include <core/rtc_schedule.h>
#include <LCD_1602_RUS.h>
#include <platform/ports.h>
namespace {
LCD_1602_RUS* lcd;
uint8_t clockField;
CalendarValue clockDraft;
bool pendingInput;
ManualUiInput nextInput;
uint32_t lastInteraction;
bool returnedHome;
void returnHomeIfIdle() {
  const auto state = applicationState();
  if (!UI_HOME_TIMEOUT_SEC || returnedHome ||
      (state != ApplicationState::Running && state != ApplicationState::ClockEditing) ||
      uint32_t(hardware::milliseconds() - lastInteraction) < UI_HOME_TIMEOUT_SEC * 1000UL) return;
  returnedHome = true;
  if (state == ApplicationState::ClockEditing && !applicationCancelClock()) return;
  manualUiShowActive(autoUiSelectedPump());
}
void drawClock() {
  calendarDraw(*lcd, clockDraft, clockField, true,
               applicationState() == ApplicationState::ClockEditing);
}
void clockInput(ManualUiInput input) {
  const int8_t turn = input == ManualUiInput::TurnRight ? 1 : input == ManualUiInput::TurnLeft ? -1 : 0;
  const int8_t held = input == ManualUiInput::HeldTurnRight ? 1 : input == ManualUiInput::HeldTurnLeft ? -1 : 0;
  if (turn) {
    const int8_t next = clockField + turn;
    const uint8_t maximum = applicationState() == ApplicationState::ClockRequired ? 5 : 6;
    clockField = next < 0 ? 0 : next > maximum ? maximum : next;
  } else if (held && clockField < 5) calendarChange(clockDraft, clockField, held);
  else if (input == ManualUiInput::Click) {
    if (clockField < 5) ++clockField;
    else {
      const bool required = applicationState() == ApplicationState::ClockRequired;
      const bool resumed = clockField == 6 ? applicationCancelClock() :
          applicationSaveClock(calendarTimestamp(clockDraft));
      if (resumed) {
        if (required) {
          autoUiBegin(*lcd);
          manualUiShowActive(autoUiSelectedPump());
        } else manualUiShowMenu(autoUiSelectedPump(), 1);
      }
      return;
    }
  }
  drawClock();
}
void handleInput() {
  if (!pendingInput) { returnHomeIfIdle(); return; }
  const auto state = applicationState();
  if (nextInput == ManualUiInput::DoubleClick) {
    if (state == ApplicationState::ClockEditing) {
      if (applicationCancelClock()) manualUiShowMenu(autoUiSelectedPump(), 1);
    } else if (state == ApplicationState::Running) {
      if (!manualUiIsOpen()) autoUiBack();
      else if (manualUiBack() == ManualUiAction::ShowPump) autoUiReset();
    }
    return;
  }
  if (state == ApplicationState::ClockRequired || state == ApplicationState::ClockEditing) {
    clockInput(nextInput);
    return;
  }
  if (!manualUiIsOpen()) { autoUiInput(nextInput); return; }
  switch (manualUiHandle(nextInput)) {
    case ManualUiAction::None: break;
    case ManualUiAction::ShowPump:
    case ManualUiAction::ReturnToAuto: autoUiReset(); break;
    case ManualUiAction::PreviousPump: autoUiMove(-1); break;
    case ManualUiAction::NextPump: autoUiMove(1); break;
    case ManualUiAction::SetClock:
      applicationOpenClock();
      clockDraft = calendarFrom(scheduleNow());
      clockField = 0;
      drawClock();
      break;
  }
}
void drawFault() {
  uiBeginFrame(*lcd);
  uiTextRow(*lcd, 0, TR(RTC_ERROR));
  uiTextRow(*lcd, 1, TR(RTC_WIRING));
}
}
void lcdApplicationBegin(LCD_1602_RUS& display, bool resetRequested, uint32_t startupTimestamp) {
  lcd = &display;
  pendingInput = false;
  lastInteraction = hardware::milliseconds();
  returnedHome = false;
  manualUiBegin(display);
  switch (applicationBegin(resetRequested)) {
    case ApplicationState::Running:
      autoUiBegin(display);
      manualUiShowActive(autoUiSelectedPump());
      break;
    case ApplicationState::ClockRequired:
      clockDraft = calendarFrom(startupTimestamp);
      clockField = 0;
      drawClock();
      break;
    case ApplicationState::Fault: drawFault(); break;
    case ApplicationState::ClockEditing: break;
  }
}
void lcdApplicationRefresh() {
  if (applicationState() != ApplicationState::Running) return;
  if (manualUiRefresh() == ManualUiAction::ReturnToAuto) autoUiReset();
  autoUiRefresh();
}
void lcdApplicationTick(bool hasInput, ManualUiInput input, bool interacting) {
  if (hasInput || interacting) {
    lastInteraction = hardware::milliseconds();
    returnedHome = false;
  }
  pendingInput = hasInput;
  nextInput = input;
  const auto before = applicationState();
  applicationTick(handleInput);
  pendingInput = false;
  if (applicationState() == ApplicationState::Fault && before != ApplicationState::Fault) drawFault();
  lcdApplicationRefresh();
}
