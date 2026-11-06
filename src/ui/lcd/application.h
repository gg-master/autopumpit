#pragma once
#include <ui/lcd/manual_ui.h>
#include <stdint.h>
class LCD_1602_RUS;
void lcdApplicationBegin(LCD_1602_RUS& display, bool resetRequested, uint32_t startupTimestamp);
void lcdApplicationTick(bool hasInput = false, ManualUiInput input = ManualUiInput::Click,
                        bool interacting = false);
void lcdApplicationRefresh();
