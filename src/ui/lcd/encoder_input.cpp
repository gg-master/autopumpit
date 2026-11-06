#include <ui/lcd/encoder_input.h>
#include <GyverEncoder.h>

namespace { constexpr uint32_t doubleClickWindow = 300UL; }

bool EncoderInput::read(Encoder& encoder, ManualUiInput& input) {
  if (turnPending) {
    turnPending = false;
    input = pendingTurn;
    return true;
  }
  encoder.tick();
  const uint32_t now = millis();
  if (encoder.isTurn()) {
    holdCandidate = false;
    if (encoder.isRightH()) input = ManualUiInput::HeldTurnRight;
    else if (encoder.isLeftH()) input = ManualUiInput::HeldTurnLeft;
    else if (encoder.isRight()) input = ManualUiInput::TurnRight;
    else input = ManualUiInput::TurnLeft;
    if (clickPending) {
      clickPending = false;
      pendingTurn = input;
      turnPending = true;
      input = ManualUiInput::Click;
    }
    return true;
  }
  if (encoder.isHolded()) { holdCandidate = true; clickPending = false; }
  else if (holdCandidate && !encoder.isHold()) {
    holdCandidate = false;
    input = ManualUiInput::Hold;
    return true;
  } else if (encoder.isClick()) {
    if (clickPending && uint32_t(now - clickedAt) <= doubleClickWindow) {
      clickPending = false;
      input = ManualUiInput::DoubleClick;
      return true;
    }
    const bool deliverPrevious = clickPending;
    clickPending = true;
    clickedAt = now;
    if (deliverPrevious) { input = ManualUiInput::Click; return true; }
  }
  if (clickPending && uint32_t(now - clickedAt) >= doubleClickWindow) {
    clickPending = false;
    input = ManualUiInput::Click;
    return true;
  }
  return false;
}