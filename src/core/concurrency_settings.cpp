#include <core/concurrency_settings.h>
#include <platform/ports.h>
#include <settings.h>

namespace {
constexpr uint16_t storageBase = 632;
constexpr uint8_t recordSize = 8;
constexpr uint8_t marker = 0xc9;
static_assert(128 + PUPM_AMOUNT * 36 <= storageBase, "Concurrency overlaps schedule storage");
static_assert(storageBase + 2 * recordSize < 1023, "Concurrency must fit EEPROM");
uint8_t limit = 1;
int8_t selectedSlot = -1;
uint16_t sequence;
uint16_t checksum(const uint8_t* bytes) {
  uint16_t crc = 0xffff;
  for (uint8_t i = 1; i < recordSize - 2; ++i) {
    crc ^= uint16_t(bytes[i]) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit)
      crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}
}
void concurrencySettingsBegin() {
  limit = 1;
  selectedSlot = -1;
  sequence = 0;
  for (uint8_t slot = 0; slot < 2; ++slot) {
    uint8_t bytes[recordSize];
    hardware::storageRead(storageBase + slot * recordSize, bytes, recordSize);
    if (bytes[0] != marker || bytes[1] != 1 || !bytes[4] || bytes[4] > PUPM_AMOUNT ||
        bytes[5] != uint8_t(~bytes[4]) ||
        checksum(bytes) != (uint16_t(bytes[6]) | (uint16_t(bytes[7]) << 8))) continue;
    const uint16_t candidate = uint16_t(bytes[2]) | (uint16_t(bytes[3]) << 8);
    const uint16_t delta = candidate - sequence;
    if (selectedSlot < 0 || (delta && delta < 0x8000)) {
      selectedSlot = slot;
      sequence = candidate;
      limit = bytes[4];
    }
  }
}
uint8_t concurrencySettingsLimit() { return limit; }
bool concurrencySettingsSetLimit(uint8_t value) {
  if (!value || value > PUPM_AMOUNT) return false;
  if (value == limit) return true;
  const uint16_t nextSequence = sequence + 1;
  uint8_t bytes[recordSize] = {marker, 1, uint8_t(nextSequence), uint8_t(nextSequence >> 8),
                             value, uint8_t(~value), 0, 0};
  const uint16_t crc = checksum(bytes);
  bytes[6] = crc;
  bytes[7] = crc >> 8;
  const uint8_t slot = selectedSlot == 0 ? 1 : 0;
  const uint16_t base = storageBase + slot * recordSize;
  hardware::storageWrite(base, 0);
  for (uint8_t i = 1; i < recordSize; ++i) hardware::storageWrite(base + i, bytes[i]);
  hardware::storageWrite(base, marker);
  hardware::storageFlush();
  selectedSlot = slot;
  sequence = nextSequence;
  limit = value;
  return true;
}
