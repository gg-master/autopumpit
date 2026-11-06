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
};

enum class ManualUiAction : uint8_t {
  None,
  ReturnToAuto,
  SetClock,
  PreviousPump,
  NextPump,
};

void manualUiBegin(LCD_1602_RUS& display);
void manualUiOpen(uint8_t pump);
void manualUiShowPump(uint8_t pump);
void manualUiClose();
ManualUiAction manualUiHandle(ManualUiInput input);
ManualUiAction manualUiRefresh();
bool manualUiIsOpen();
