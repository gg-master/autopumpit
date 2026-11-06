#pragma once
#include <avr/pgmspace.h>
#include <stdint.h>
#include <settings.h>

#if UI_LANGUAGE == 0
#include <locales/en.h>
#elif UI_LANGUAGE == 1
#include <locales/ru.h>
#else
#error "UI_LANGUAGE must be 0 (English) or 1 (Russian)"
#endif
#define TR(key) PSTR(TXT_##key)

class LCD_1602_RUS;
void uiBeginFrame(LCD_1602_RUS& lcd);
void uiRow(LCD_1602_RUS& lcd, uint8_t row, const char* text, char marker = 0);
void uiTextRow(LCD_1602_RUS& lcd, uint8_t row, PGM_P text, char marker = 0);
void uiFormatRow(LCD_1602_RUS& lcd, uint8_t row, PGM_P format, ...);
void uiActions(LCD_1602_RUS& lcd, uint8_t row, PGM_P first, PGM_P second,
               uint8_t selected, uint8_t offset = 0);
void uiPumpRow(LCD_1602_RUS& lcd, uint8_t row, uint8_t pump, char marker = 0, PGM_P prefix = nullptr);