#include <Arduino.h>
#include <RTClib.h>
#include <Wire.h>
#include <avr/eeprom.h>
#include <settings.h>
#include <platform/ports.h>
namespace {
#if USE_DS3231
RTC_DS3231 rtc;
#else
RTC_DS1307 rtc;
#endif
}
namespace hardware {
uint32_t milliseconds() { return millis(); }
void configureOutput(uint8_t pin) { pinMode(pin, OUTPUT); }
void writeOutput(uint8_t pin, bool level) { digitalWrite(pin, level); }
bool clockBegin() { return rtc.begin(); }
bool clockLostPower() {
#if USE_DS3231
  return rtc.lostPower();
#else
  return !rtc.isrunning();
#endif
}
bool clockRead(uint32_t& timestamp) {
  Wire.beginTransmission(0x68);
  if (Wire.endTransmission() != 0 || clockLostPower()) return false;
  const DateTime value = rtc.now();
  if (!value.isValid()) return false;
  timestamp = value.unixtime();
  return true;
}
void clockAdjust(uint32_t timestamp) { rtc.adjust(DateTime(timestamp)); }
void storageRead(uint16_t address, uint8_t* data, uint16_t count) {
  eeprom_read_block(data, reinterpret_cast<const void*>(address), count);
}
void storageWrite(uint16_t address, uint8_t value) {
  eeprom_update_byte(reinterpret_cast<uint8_t*>(address), value);
}
void storageFlush() { eeprom_busy_wait(); }
}
