#pragma once
#include <stdint.h>
using boolean = bool;
constexpr uint8_t INPUT = 0;
constexpr uint8_t INPUT_PULLUP = 2;
uint32_t millis();
int digitalRead(uint8_t pin);
void pinMode(uint8_t pin, uint8_t mode);
using byte = uint8_t;
