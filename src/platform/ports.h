#pragma once
#include <stdint.h>
namespace hardware {
uint32_t milliseconds();
void configureOutput(uint8_t pin);
// Before configureOutput, preload the output latch without driving the pin.
void writeOutput(uint8_t pin, bool level);
bool clockBegin();
bool clockLostPower();
bool clockRead(uint32_t& timestamp);
void clockAdjust(uint32_t timestamp);
void storageRead(uint16_t address, uint8_t* data, uint16_t count);
void storageWrite(uint16_t address, uint8_t value);
void storageFlush();
}
