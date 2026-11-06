#pragma once
#include <stdint.h>
#include <settings.h>
class LCD_1602_RUS;
enum class Screen : uint8_t { Selector, Pump, Concurrency, Active, Menu };
struct ManualUiState {
  LCD_1602_RUS* lcd{};
  Screen screen{};
  bool open{};
  bool dirty{};
  uint8_t pump{};
  uint8_t cursor{};
  uint8_t concurrencyDraft{};
  uint16_t lastActiveMask = UINT16_MAX;
  uint16_t lastActiveManualMask = 0;
  bool manualAtOpen{};
  uint32_t lastRemaining = UINT32_MAX;
  bool lastPending{};
  bool lastWaiting{};
  const char* errorText{};
};
extern ManualUiState manualState;
void manualUiRender();
