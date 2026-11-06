#include <Arduino.h>
#include <RTClib.h>
#include <GyverEncoder.h>
#include <LCD_1602_RUS.h>
#include <ui/lcd/controller.h>
#include <ui/lcd/application.h>
#include <ui/lcd/encoder_input.h>
#include <ui/lcd/i18n.h>
#include <core/application.h>
#include <settings.h>
namespace {
Encoder encoder(CLK, DT, SW);
LCD_1602_RUS lcd(DRIVER_VERSION ? 0x27 : 0x3f, 16, 2);
EncoderInput encoderInput;
bool backlight = true;
uint32_t lastAction;
}
void lcdControllerBegin() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  encoder.setType(ENCODER_TYPE);
  if (ENC_REVERSE) encoder.setDirection(REVERSE);
  const bool reset = !digitalRead(SW);
  if (reset) {
    uiTextRow(lcd, 0, TR(RESET));
    while (!digitalRead(SW)) {}
  }
  lcdApplicationBegin(lcd, reset, DateTime(__DATE__, __TIME__).unixtime());
}
void lcdControllerTick() {
  ManualUiInput input = ManualUiInput::Click;
  bool hasInput = encoderInput.read(encoder, input);
  if (hasInput) {
    lastAction = millis();
    if (!backlight) {
      backlight = true;
      lcd.backlight();
      hasInput = false;
    }
  }
  const auto before = applicationState();
  lcdApplicationTick(hasInput, input);
  if (applicationState() == ApplicationState::Fault && before != ApplicationState::Fault) {
    backlight = true;
    lastAction = millis();
    lcd.backlight();
  }
  if (LCD_BACKL && backlight && millis() - lastAction >= BACKL_TOUT * 1000UL) {
    backlight = false;
    lcd.noBacklight();
  }
}
