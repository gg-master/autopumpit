#pragma once
#include <array>
#include <stdint.h>
#include <string>
// Records logical LCD cells. Physical font/CGRAM limits are checked separately.
class LCD_1602_RUS {
  std::array<std::array<char32_t, 16>, 2> cells;
  uint8_t col = 0, row = 0;
  void write(char32_t value) { if (col < 16) cells[row][col] = value; ++col; }
 public:
  LCD_1602_RUS() { clear(); }
  void clear() { for (auto& line : cells) line.fill(U' '); col = row = 0; }
  void setCursor(uint8_t x, uint8_t y) { col = x; row = y; }
  void print(char value) { write(static_cast<uint8_t>(value)); }
  void print(const char* text) {
    while (*text) {
      const uint8_t first = *text++;
      if ((first & 0xe0) == 0xc0 && *text) write(((first & 31) << 6) | (uint8_t(*text++) & 63));
      else write(first);
    }
  }
  void print(const wchar_t* text) { while (*text) write(*text++); }
  std::string line(uint8_t number) const {
    std::string result;
    for (char32_t value : cells[number]) {
      if (value < 128) result += char(value);
      else { result += char(0xc0 | (value >> 6)); result += char(0x80 | (value & 63)); }
    }
    return result;
  }
};
