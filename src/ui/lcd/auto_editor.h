#pragma once
#include <ui/lcd/manual_ui.h>
class LCD_1602_RUS;
void autoUiBegin(LCD_1602_RUS& lcd);
void autoUiReset();
void autoUiRefresh();
void autoUiInput(ManualUiInput input);

void autoUiMove(int8_t step);

uint8_t autoUiSelectedPump();

void autoUiBack();
