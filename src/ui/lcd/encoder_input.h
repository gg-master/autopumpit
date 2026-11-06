#pragma once
#include <ui/lcd/manual_ui.h>
class Encoder;
class EncoderInput {
  bool holdCandidate = false;
 public:
  bool read(Encoder& encoder, ManualUiInput& input);
};
