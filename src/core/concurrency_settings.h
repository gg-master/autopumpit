#pragma once
#include <stdint.h>

void concurrencySettingsBegin();
uint8_t concurrencySettingsLimit();
bool concurrencySettingsSetLimit(uint8_t limit);
