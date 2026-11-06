#include <ui/lcd/auto_editor.h>
#include <ui/lcd/calendar_ui.h>
#include <ui/lcd/i18n.h>
#include <ui/lcd/manual_ui.h>
#include <core/program_settings.h>
#include <core/pump_control.h>
#include <core/rtc_schedule.h>
#include <settings.h>
#include <LCD_1602_RUS.h>
#include <stdio.h>

namespace {
enum class Field : uint8_t {
  Heading, Day, Month, Year, StartHour, StartMinute,
  PauseHour, PauseMinute, PauseSecond, RunHour, RunMinute, RunSecond, Save, Cancel,
};
enum class FieldKind : uint8_t { Heading, Calendar, Pause, Run, Save, Cancel };
struct FieldDefinition {
  Field field;
  FieldKind kind;
  uint8_t component;
};
const FieldDefinition fields[] = {
  {Field::Heading, FieldKind::Heading, 0},
  {Field::Day, FieldKind::Calendar, 0},
  {Field::Month, FieldKind::Calendar, 1},
  {Field::Year, FieldKind::Calendar, 2},
  {Field::StartHour, FieldKind::Calendar, 3},
  {Field::StartMinute, FieldKind::Calendar, 4},
  {Field::PauseHour, FieldKind::Pause, 0},
  {Field::PauseMinute, FieldKind::Pause, 1},
  {Field::PauseSecond, FieldKind::Pause, 2},
  {Field::RunHour, FieldKind::Run, 0},
  {Field::RunMinute, FieldKind::Run, 1},
  {Field::RunSecond, FieldKind::Run, 2},
  {Field::Save, FieldKind::Save, 0},
  {Field::Cancel, FieldKind::Cancel, 0},
};
const FieldDefinition* current = fields;
LCD_1602_RUS* lcd;
int8_t current_pump;
uint32_t shownDue = UINT32_MAX;
CalendarValue draftDate;
uint32_t draftPause;
uint32_t draftRun;
bool draftDirty;
const FieldDefinition* adjacentField(int8_t direction) {
  if (direction < 0) return current == fields ? current : current - 1;
  const auto* last = fields + sizeof(fields) / sizeof(fields[0]) - 1;
  return current == last ? current : current + 1;
}
void loadDraft() {
  uint32_t due = scheduleNext(current_pump);
  if (!due || due <= scheduleNow()) due = (scheduleNow() / 60 + 1) * 60;
  draftDate = calendarFrom(due);
  draftPause = programPause(current_pump);
  draftRun = programRun(current_pump);
  draftDirty = false;
}
void drawAuto() {
  if (current->kind == FieldKind::Calendar) {
    calendarDraw(*lcd, draftDate, current->component);
    return;
  }
  char row[17];
  uiBeginFrame(*lcd);
  uiPumpRow(*lcd, 0, current_pump, '>');
  if (current->field == Field::Heading) {
    shownDue = scheduleNext(current_pump);
    if (!shownDue) {
      uiTextRow(*lcd, 1, TR(DISABLED));
    } else {
      const CalendarValue next = calendarFrom(shownDue);
      snprintf(row, sizeof(row), "%02u.%02u %02u:%02u:%02u", next.day, next.month,
               next.hour, next.minute, uint8_t(shownDue % 60));
      lcdRow(*lcd, 1, row);
    }
  } else if (current->field == Field::Save || current->field == Field::Cancel) {
    uiActions(*lcd, 1, TR(SAVE), TR(CANCEL), current->field == Field::Save ? 0 : 1);
  } else {
    const bool pause = current->kind == FieldKind::Pause;
    const uint32_t value = pause ? draftPause : draftRun;
    const uint8_t component = current->component;
    uiFormatRow(*lcd, 1, pause ? TR(PAUSE_TIME) : TR(RUN_TIME),
                component == 0 ? '>' : ' ', uint16_t(value / 3600),
                component == 1 ? '>' : ':', uint8_t(value % 3600 / 60),
                component == 2 ? '>' : ':', uint8_t(value % 60));
  }
}
void autoError(PGM_P text) {
  uiBeginFrame(*lcd);
  uiPumpRow(*lcd, 0, current_pump, '>');
  uiTextRow(*lcd, 1, text);
}
bool saveDraft() {
  if (!draftDirty) return true;
  switch (programConfigure(current_pump, draftPause, draftRun, calendarTimestamp(draftDate))) {
    case ProgramSaveResult::Busy: autoError(TR(PUMP_BUSY)); return false;
    case ProgramSaveResult::PastStart: autoError(TR(START_PAST)); return false;
    case ProgramSaveResult::Saved: draftDirty = false; return true;
  }
  return false;
}
void changeDuration(uint32_t& value, uint8_t component, int8_t step) {
  uint8_t h = value / 3600, m = value % 3600 / 60, s = value % 60;
  uint8_t* part = component == 0 ? &h : component == 1 ? &m : &s;
  const int16_t next = int16_t(*part) + step;
  const uint8_t maximum = component == 0 ? 99 : 59;
  *part = next < 0 ? 0 : next > maximum ? maximum : next;
  value = uint32_t(h) * 3600UL + uint32_t(m) * 60UL + s;
}
void changeField(int8_t step) {
  switch (current->kind) {
    case FieldKind::Calendar: calendarChange(draftDate, current->component, step); break;
    case FieldKind::Pause: changeDuration(draftPause, current->component, step); break;
    case FieldKind::Run: changeDuration(draftRun, current->component, step); break;
    case FieldKind::Heading: return;
    case FieldKind::Save:
    case FieldKind::Cancel: return;
  }
  draftDirty = true;
}
}
void autoUiBegin(LCD_1602_RUS& display) { lcd = &display; autoUiReset(); }
void autoUiReset() {
  current = fields;
  loadDraft();
  if (pumpControlManualMode(current_pump)) manualUiShowPump(current_pump);
  else drawAuto();
}
void autoUiMove(int8_t step) {
  manualUiClose();
  const int8_t next = current_pump + step;
  current_pump = next < 0 ? 0 : next >= PUPM_AMOUNT ? PUPM_AMOUNT - 1 : next;
  autoUiReset();
}
void autoUiRefresh() {
  if (!manualUiIsOpen() && current->field == Field::Heading && shownDue != scheduleNext(current_pump)) drawAuto();
}
void autoUiInput(ManualUiInput input) {
  const int8_t turn = input == ManualUiInput::TurnRight ? 1 :
                      input == ManualUiInput::TurnLeft ? -1 : 0;
  const int8_t held = input == ManualUiInput::HeldTurnRight ? 1 :
                      input == ManualUiInput::HeldTurnLeft ? -1 : 0;
  if (input == ManualUiInput::Hold) {
    if (current->field == Field::Heading) { programResetPump(current_pump); autoUiReset(); }
    return;
  }
  if (turn) {
    if (current->field == Field::Heading && turn > 0) loadDraft();
    const auto* next = adjacentField(turn);
    if (next->field == Field::Heading && current->field != Field::Heading && !saveDraft()) return;
    current = next;
  } else if (held) {
    if (current->field == Field::Heading) { autoUiMove(held); return; }
    changeField(held);
  } else {
    switch (current->kind) {
      case FieldKind::Heading: manualUiOpen(current_pump); return;
      case FieldKind::Save:
        if (!saveDraft()) return;
        current = fields;
        break;
      case FieldKind::Cancel:
        current = fields;
        loadDraft();
        break;
      case FieldKind::Calendar:
      case FieldKind::Pause:
      case FieldKind::Run: current = adjacentField(1); break;
    }
  }
  drawAuto();
}
