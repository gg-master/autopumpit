#pragma once

#include <stdint.h>

class LCD_1602_RUS;

enum class ManualUiInput : uint8_t {
  TurnLeft,
  TurnRight,
  HeldTurnLeft,
  HeldTurnRight,
  Click,
  Hold,
  DoubleClick,
};

enum class ManualUiAction : uint8_t {
  None,
  ReturnToAuto,
  ShowPump,
  SetClock,
  PreviousPump,
  NextPump,
};

void manualUiBegin(LCD_1602_RUS& display);
void manualUiOpen(uint8_t pump);
void manualUiShowPump(uint8_t pump);
void manualUiShowActive(uint8_t pump);
void manualUiShowMenu(uint8_t pump, uint8_t selected = 0);
void manualUiClose();
ManualUiAction manualUiHandle(ManualUiInput input);
ManualUiAction manualUiRefresh();
ManualUiAction manualUiBack();
bool manualUiIsOpen();
