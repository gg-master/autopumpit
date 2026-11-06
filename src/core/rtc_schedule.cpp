#include <platform/ports.h>
#include <settings.h>
#include <core/rtc_schedule.h>

namespace {
constexpr uint16_t storageBase = 128;
constexpr uint8_t recordSize = 18;
constexpr uint8_t marker = 0xa7;
static_assert(storageBase + PUPM_AMOUNT * 2 * recordSize < 1023,
              "Schedule must fit beside startup flag");
PumpProgram programs[PUPM_AMOUNT];
uint16_t sequences[PUPM_AMOUNT];
int8_t slots[PUPM_AMOUNT];
uint32_t wallNow;
uint32_t lastRead;
bool needsClock;

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
  hardware::storageRead(address(pump, slot), bytes, recordSize);
  if (bytes[0] != marker || bytes[1] != 1 ||
      checksum(bytes, pump) != (uint16_t(bytes[16]) | (uint16_t(bytes[17]) << 8)))
    return false;
  record = {uint16_t(uint16_t(bytes[2]) | (uint16_t(bytes[3]) << 8)),
            get32(bytes + 4), get32(bytes + 8), get32(bytes + 12)};
  return true;
}

void saveRecord(uint8_t pump, const PumpProgram& program) {
  uint8_t bytes[recordSize] = {marker, 1};
  const uint16_t sequence = sequences[pump] + 1;
  bytes[2] = sequence;
  bytes[3] = sequence >> 8;
  put32(bytes + 4, program.next);
  put32(bytes + 8, program.pause);
  put32(bytes + 12, program.run);
  const uint16_t crc = checksum(bytes, pump);
  bytes[16] = crc;
  bytes[17] = crc >> 8;
  const uint8_t slot = slots[pump] == 0 ? 1 : 0;
  const uint16_t base = address(pump, slot);
  // Invalidate only the older copy; commit the new copy with its marker last.
  hardware::storageWrite(base, 0);
  for (uint8_t i = 1; i < recordSize; ++i)
    hardware::storageWrite(base + i, bytes[i]);
  hardware::storageWrite(base, marker);
  hardware::storageFlush();
  slots[pump] = slot;
  sequences[pump] = sequence;
}

bool readClock() {
  uint32_t timestamp;
  if (!hardware::clockRead(timestamp) || timestamp < wallNow) return false;
  wallNow = timestamp;
  lastRead = hardware::milliseconds();
  return true;
}
}  // namespace

bool scheduleBegin(bool reset) {
  needsClock = true;
  wallNow = 0;
  for (uint8_t pump = 0; pump < PUPM_AMOUNT; ++pump) {
    slots[pump] = -1;
    sequences[pump] = 0;
    Record selected{};
    for (uint8_t slot = 0; slot < 2; ++slot) {
      if (reset) hardware::storageWrite(address(pump, slot), 0);
      Record candidate{};
      if (!readRecord(pump, slot, candidate)) continue;
      const uint16_t delta = candidate.sequence - selected.sequence;
      if (slots[pump] < 0 || (delta != 0 && delta < 0x8000)) {
        selected = candidate;
        slots[pump] = slot;
      }
    }
    programs[pump] = {selected.pause, selected.run, selected.due};
    if (slots[pump] >= 0) sequences[pump] = selected.sequence;
    else saveRecord(pump, programs[pump]);
  }
  if (!hardware::clockBegin()) return false;
  if (!hardware::clockLostPower()) needsClock = !readClock();
  return true;
}

bool scheduleTick() {
  return !needsClock && (hardware::milliseconds() - lastRead < 250 || readClock());
}

uint32_t scheduleNow() { return wallNow; }
uint32_t scheduleNext(uint8_t pump) { return programs[pump].next; }
const PumpProgram& scheduleProgram(uint8_t pump) { return programs[pump]; }
bool scheduleNeedsClock() { return needsClock; }

bool scheduleSetClock(uint32_t timestamp) {
  if (timestamp < 946684800UL || timestamp > 4102444799UL) return false;
  hardware::clockAdjust(timestamp);
  wallNow = 0;
  needsClock = !readClock();
  return !needsClock;
}

bool scheduleConfigureAt(uint8_t pump, uint32_t pause, uint32_t run, uint32_t first) {
  if (needsClock || pump >= PUPM_AMOUNT) return false;
  if (pause && run && (first <= wallNow || first > 4102444799UL)) return false;
  const PumpProgram next{pause, run, pause && run ? first : 0};
  saveRecord(pump, next);
  programs[pump] = next;
  return true;
}

bool scheduleDue(uint8_t pump) {
  return programs[pump].next != 0 && wallNow >= programs[pump].next;
}

namespace {
void setDeadline(uint8_t pump, uint32_t deadline) {
  PumpProgram next = programs[pump];
  next.next = deadline;
  saveRecord(pump, next);
  programs[pump] = next;
}
}

void scheduleStarted(uint8_t pump) {
  // Commit before energizing: a reboot never resumes an interrupted dose.
  const PumpProgram& program = programs[pump];
  setDeadline(pump, wallNow + program.pause + (TIMER_START ? program.run : 0));
}

void scheduleStopped(uint8_t pump) {
  if (TIMER_START) scheduleInterrupted(pump);
}

void scheduleInterrupted(uint8_t pump) {
  const PumpProgram& program = programs[pump];
  setDeadline(pump, program.pause && program.run ? wallNow + program.pause : 0);
}
