#include <ui/lcd/encoder_input.h>
#include <GyverEncoder.h>
#include <settings.h>
#include <array>
#include <iostream>
namespace {
uint32_t ticks;
std::array<bool, 32> pins = {true, true, true, true};
Encoder encoder(CLK, DT, SW);
EncoderInput inputReader;
}
uint32_t millis() { return ticks; }
int digitalRead(uint8_t pin) { return pins[pin]; }
void pinMode(uint8_t, uint8_t) {}
int main() {
  encoder.setType(ENCODER_TYPE);
  if (ENC_REVERSE) encoder.setDirection(REVERSE);
  bool button, clk, dt;
  while (std::cin >> ticks >> button >> clk >> dt) {
    pins[SW] = button; pins[CLK] = clk; pins[DT] = dt;
    ManualUiInput input;
    if (inputReader.read(encoder, input)) std::cout << ticks << ' ' << unsigned(input) << '\n';
  }
}
