#include <Arduino.h>
#include <RTClib.h>
#include <Wire.h>
#include <avr/eeprom.h>
#include <config.h>
#include <rtc_schedule.h>

namespace {
#if USE_DS3231
RTC_DS3231 rtc;
#else
RTC_DS1307 rtc;
#endif
constexpr uint16_t storageBase = 128;
constexpr uint8_t recordSize = 18;
constexpr uint8_t marker = 0xa7;
static_assert(storageBase + PUPM_AMOUNT * 2 * recordSize < 1023,
              "Schedule must fit beside legacy settings and startup flag");
uint32_t nextDue[PUPM_AMOUNT];
uint16_t sequences[PUPM_AMOUNT];
int8_t slots[PUPM_AMOUNT];
uint32_t wallNow;
uint32_t lastRead;

struct Record {
  uint16_t sequence;
  uint32_t due;
  uint32_t pause;
  uint32_t run;
};

uint16_t address(uint8_t pump, uint8_t slot) {
  return storageBase + (pump * 2 + slot) * recordSize;
}

uint16_t checksum(const uint8_t* bytes, uint8_t pump) {
  uint16_t crc = 0xffff ^ pump;
  for (uint8_t i = 1; i < recordSize - 2; ++i) {
    crc ^= static_cast<uint16_t>(bytes[i]) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit)
      crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}

uint32_t get32(const uint8_t* bytes) {
  return uint32_t(bytes[0]) | (uint32_t(bytes[1]) << 8) |
         (uint32_t(bytes[2]) << 16) | (uint32_t(bytes[3]) << 24);
}

void put32(uint8_t* bytes, uint32_t value) {
  for (uint8_t i = 0; i < 4; ++i) bytes[i] = value >> (8 * i);
}

bool readRecord(uint8_t pump, uint8_t slot, Record& record) {
  uint8_t bytes[recordSize];
  eeprom_read_block(bytes, reinterpret_cast<const void*>(address(pump, slot)), recordSize);
  if (bytes[0] != marker || bytes[1] != 1 ||
      checksum(bytes, pump) != (uint16_t(bytes[16]) | (uint16_t(bytes[17]) << 8)))
    return false;
  record = {uint16_t(uint16_t(bytes[2]) | (uint16_t(bytes[3]) << 8)),
            get32(bytes + 4), get32(bytes + 8), get32(bytes + 12)};
  return true;
}

void saveRecord(uint8_t pump, uint32_t pause, uint32_t run) {
  uint8_t bytes[recordSize] = {marker, 1};
  const uint16_t sequence = sequences[pump] + 1;
  bytes[2] = sequence;
  bytes[3] = sequence >> 8;
  put32(bytes + 4, nextDue[pump]);
  put32(bytes + 8, pause);
  put32(bytes + 12, run);
  const uint16_t crc = checksum(bytes, pump);
  bytes[16] = crc;
  bytes[17] = crc >> 8;
  const uint8_t slot = slots[pump] == 0 ? 1 : 0;
  const uint16_t base = address(pump, slot);
  // Invalidate only the older copy; commit the new copy with its marker last.
  eeprom_update_byte(reinterpret_cast<uint8_t*>(base), 0);
  for (uint8_t i = 1; i < recordSize; ++i)
    eeprom_update_byte(reinterpret_cast<uint8_t*>(base + i), bytes[i]);
  eeprom_update_byte(reinterpret_cast<uint8_t*>(base), marker);
  eeprom_busy_wait();
  slots[pump] = slot;
  sequences[pump] = sequence;
}

bool readClock() {
  Wire.beginTransmission(0x68);
  if (Wire.endTransmission() != 0) return false;
#if USE_DS3231
  if (rtc.lostPower()) return false;
#else
  if (!rtc.isrunning()) return false;
#endif
  const DateTime value = rtc.now();
  if (!value.isValid() || value.unixtime() < wallNow) return false;
  wallNow = value.unixtime();
  lastRead = millis();
  return true;
}
}  // namespace

bool scheduleBegin(bool reset, uint32_t* pauses, uint32_t* runs) {
  if (!rtc.begin()) return false;
#if USE_DS3231
  const bool clockReset = rtc.lostPower();
#else
  const bool clockReset = !rtc.isrunning();
#endif
  if (clockReset) rtc.adjust(DateTime(__DATE__, __TIME__));
  if (!readClock()) return false;
  for (uint8_t pump = 0; pump < PUPM_AMOUNT; ++pump) {
    slots[pump] = -1;
    sequences[pump] = 0;
    Record selected{};
    for (uint8_t slot = 0; slot < 2; ++slot) {
      if (reset) eeprom_update_byte(reinterpret_cast<uint8_t*>(address(pump, slot)), 0);
      Record candidate{};
      if (!readRecord(pump, slot, candidate)) continue;
      const uint16_t delta = candidate.sequence - selected.sequence;
      if (slots[pump] < 0 || (delta != 0 && delta < 0x8000)) {
        selected = candidate;
        slots[pump] = slot;
      }
    }
    const bool saved = slots[pump] >= 0;
    if (saved) {
      sequences[pump] = selected.sequence;
      pauses[pump] = selected.pause;
      runs[pump] = selected.run;
    }
    nextDue[pump] = saved && !clockReset ? selected.due :
        (pauses[pump] && runs[pump] ? wallNow + pauses[pump] : 0);
    if (!saved || clockReset) saveRecord(pump, pauses[pump], runs[pump]);
  }
  return true;
}

bool scheduleTick() {
  return millis() - lastRead < 250 || readClock();
}

bool scheduleDue(uint8_t pump) {
  return nextDue[pump] != 0 && wallNow >= nextDue[pump];
}

void scheduleConfigure(uint8_t pump, uint32_t pause, uint32_t run) {
  Record saved{};
  if (slots[pump] >= 0 && readRecord(pump, slots[pump], saved) &&
      saved.pause == pause && saved.run == run) return;
  nextDue[pump] = pause && run ? wallNow + pause : 0;
  saveRecord(pump, pause, run);
}

void scheduleStarted(uint8_t pump, uint32_t pause, uint32_t run) {
  // Persist before energizing: a reboot never resumes an interrupted dose.
  nextDue[pump] = wallNow + pause + (TIMER_START ? run : 0);
  saveRecord(pump, pause, run);
}

void scheduleStopped(uint8_t pump, uint32_t pause, uint32_t run) {
  if (TIMER_START) {
    nextDue[pump] = pause && run ? wallNow + pause : 0;
    saveRecord(pump, pause, run);
  }
}
