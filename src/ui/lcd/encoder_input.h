#pragma once
#include <ui/lcd/manual_ui.h>
class Encoder;
class EncoderInput {
  bool holdCandidate = false;
  bool clickPending = false;
  uint32_t clickedAt = 0;
 public:
  bool read(Encoder& encoder, ManualUiInput& input);
  bool waitingForClick() const { return clickPending; }
};
