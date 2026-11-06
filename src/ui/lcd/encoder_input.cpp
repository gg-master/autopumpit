#include <ui/lcd/encoder_input.h>
#include <GyverEncoder.h>

bool EncoderInput::read(Encoder& encoder, ManualUiInput& input) {
  encoder.tick();
  if (encoder.isTurn()) {
    holdCandidate = false;
    if (encoder.isRightH()) input = ManualUiInput::HeldTurnRight;
    else if (encoder.isLeftH()) input = ManualUiInput::HeldTurnLeft;
    else if (encoder.isRight()) input = ManualUiInput::TurnRight;
    else input = ManualUiInput::TurnLeft;
    return true;
  }
  if (encoder.isHolded()) holdCandidate = true;
  else if (holdCandidate && !encoder.isHold()) {
    holdCandidate = false;
    input = ManualUiInput::Hold;
    return true;
  } else if (encoder.isClick()) {
    input = ManualUiInput::Click;
    return true;
  }
  return false;
}
