/*  ВЕРСИЯ 2.0! Установи новую версию библиотеки из реопзитория!
   Система управляет количеством помп PUPM_AMOUNT, подключенных подряд в пины платы, начиная с пина START_PIN.
   На каждую помпу заводится таймер, который включает помпу на заданное время через заданные промежутки времени.

   Включение производится сигналом уровня SWITCH_LEVEL. 0 - для реле низкого уровня (0 Вольт, все семейные модули реле),
   1 - высокого уровня (5 Вольт, редкие модули реле, все мосфеты).
   Примечание: катушка реле кушает около 60 мА, несколько включенных вместе катушек создадут лишнюю нагрузку
   на линию питания. Также несколько включенных одновременно помп сделают то же самое. Для устранения этого эффекта
   есть настройка PARALLEL. При её отключении помпы будут "вставать в очередь", совместное включение будет исключено.

   Управление:
   Поворот - смена позиции стрелки
   Удержанный поворот - изменение значения
   Крути энкодер дальше настройки секунд ПЕРИОДА, чтобы перейти к настройке времени РАБОТЫ!
   Кнопка энкодера удерживается при включении системы - сброс настроек

   Интерфейс отображается на дисплее 1602 с драйвером на I2C. Версий драйвера существует две.
   Смотри настройку DRIVER_VERSION ниже.

   Версия 2.0: новая система таймеров и меню
   Версия 2.1: автоотключение дисплея и включение по действию с энкодера
*/

#include <Arduino.h>
#include <config.h>
#include <channel_names.h>
#include <rtc_schedule.h>

void rtcError();
void backlTick();
void backlOn();
void periodTick();
void flowTick();
void encoderTick();
void changeSettings(int increment);
void drawLabels();
void changeSet();
void s_to_hms(uint32_t period);
uint32_t hms_to_s();
void drawArrow(byte col, byte row);
void update_EEPROM();

#include "GyverEncoder.h"
Encoder enc1(CLK, DT, SW);

#include <EEPROMex.h>
#include <EEPROMVar.h>

#include "LCD_1602_RUS.h"

// -------- АВТОВЫБОР ОПРЕДЕЛЕНИЯ ДИСПЛЕЯ-------------
// Если кончается на 4Т - это 0х27. Если на 4АТ - 0х3f
#if (DRIVER_VERSION)
LCD_1602_RUS lcd(0x27, 16, 2);
#else
LCD_1602_RUS lcd(0x3f, 16, 2);
#endif
// -------- АВТОВЫБОР ОПРЕДЕЛЕНИЯ ДИСПЛЕЯ-------------

uint32_t pump_timers[PUPM_AMOUNT];
uint32_t pumping_time[PUPM_AMOUNT];
uint32_t period_time[PUPM_AMOUNT];
boolean pump_state[PUPM_AMOUNT];
byte pump_pins[PUPM_AMOUNT];

int8_t current_set;
int8_t current_pump;
boolean now_pumping;

int8_t thisH, thisM, thisS;
long thisPeriod;
boolean rtcReady = false;

boolean backlState = true;
uint32_t backlTimer;

void setup() {
  // --------------------- КОНФИГУРИРУЕМ ПИНЫ ---------------------
  for (byte i = 0; i < PUPM_AMOUNT; i++) {            // пробегаем по всем помпам
    pump_pins[i] = START_PIN + i;                     // настраиваем массив пинов
    pinMode(START_PIN + i, OUTPUT);                   // настраиваем пины
    digitalWrite(START_PIN + i, !SWITCH_LEVEL);       // выключаем от греха
  }
  // --------------------- ИНИЦИАЛИЗИРУЕМ ЖЕЛЕЗО ---------------------
  //Serial.begin(9600);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  //enc1.setStepNorm(1);
  //attachInterrupt(0, encISR, CHANGE);
  enc1.setType(ENCODER_TYPE);
  if (ENC_REVERSE) enc1.setDirection(REVERSE);

  const bool resetSchedule = !digitalRead(SW) || EEPROM.read(1023) != 5;

  // --------------------- СБРОС НАСТРОЕК ---------------------
  if (!digitalRead(SW)) {          // если нажат энкодер, сбросить настройки до 1
    lcd.setCursor(0, 0);
    lcd.print("Reset settings");
    for (uint16_t i = 0; i < 8 * PUPM_AMOUNT; i += sizeof(uint32_t)) {
      EEPROM.writeLong(i, 0);
    }
  }
  while (!digitalRead(SW));        // ждём отпускания кнопки
  lcd.clear();                     // очищаем дисплей, продолжаем работу

  // --------------------------- НАСТРОЙКИ ---------------------------
  // в ячейке 1023 должен быть записан флажок, если его нет - делаем (ПЕРВЫЙ ЗАПУСК)
  if (EEPROM.read(1023) != 5) {
    EEPROM.writeByte(1023, 5);

    // обнуляем настройки каналов; расписание хранится отдельно
    for (uint16_t i = 0; i < 8 * PUPM_AMOUNT; i += sizeof(uint32_t)) {
      EEPROM.writeLong(i, 0);
    }
  }

  for (byte i = 0; i < PUPM_AMOUNT; i++) {            // пробегаем по всем помпам
    period_time[i] = EEPROM.readLong(8 * i);          // пауза в секундах
    pumping_time[i] = EEPROM.readLong(8 * i + 4);     // работа в секундах

    if (SWITCH_LEVEL)			// вырубить все помпы
      pump_state[i] = 0;
    else
      pump_state[i] = 1;
  }

  rtcReady = scheduleBegin(resetSchedule, period_time, pumping_time);
  if (!rtcReady) {
    rtcError();
    return;
  }

  // ---------------------- ВЫВОД НА ДИСПЛЕЙ ------------------------
  drawLabels();
  changeSet();
}

void loop() {
  if (!rtcReady) return;
  if (!scheduleTick()) {
    rtcReady = false;
    rtcError();
    return;
  }
  encoderTick();
  periodTick();
  flowTick();
  backlTick();
}

void rtcError() {
  for (byte i = 0; i < PUPM_AMOUNT; ++i) {
    digitalWrite(pump_pins[i], !SWITCH_LEVEL);
    pump_state[i] = !SWITCH_LEVEL;
  }
  now_pumping = false;
  lcd.clear();
  lcd.backlight();
  lcd.print("RTC error");
  lcd.setCursor(0, 1);
  lcd.print("Check RTC wiring");
}

void backlTick() {
  if (LCD_BACKL && backlState && millis() - backlTimer >= BACKL_TOUT * 1000UL) {
    backlState = false;
    lcd.noBacklight();
  }
}
void backlOn() {
  backlState = true;
  backlTimer = millis();
  lcd.backlight();
}

void periodTick() {
  for (byte i = 0; i < PUPM_AMOUNT; i++) {            // пробегаем по всем помпам
    if (period_time[i] > 0
        && pumping_time[i] > 0
        && scheduleDue(i)
        && (pump_state[i] != SWITCH_LEVEL)
        && (PARALLEL || !now_pumping)) {
      scheduleStarted(i, period_time[i], pumping_time[i]);
      pump_state[i] = SWITCH_LEVEL;
      digitalWrite(pump_pins[i], SWITCH_LEVEL);
      pump_timers[i] = millis();
      now_pumping = true;
      //Serial.println("Pump #" + String(i) + " ON");
    }
  }
}

void flowTick() {
  for (byte i = 0; i < PUPM_AMOUNT; i++) {            // пробегаем по всем помпам
    if ((period_time[i] == 0 || millis() - pump_timers[i] >= pumping_time[i] * 1000UL)
        && (pump_state[i] == SWITCH_LEVEL) ) {
      pump_state[i] = !SWITCH_LEVEL;
      digitalWrite(pump_pins[i], !SWITCH_LEVEL);
      if (TIMER_START) pump_timers[i] = millis();
      scheduleStopped(i, period_time[i], pumping_time[i]);
      now_pumping = false;
      //Serial.println("Pump #" + String(i) + " OFF");
    }
  }
}

/*
  void encISR() {
  enc1.tick();  // отработка энкодера
  }
*/

void encoderTick() {
  enc1.tick();    // отработка энкодера

  if (enc1.isTurn()) {                               // если был совершён поворот
    if (backlState) {
      backlTimer = millis();      // сбросить таймаут дисплея
      if (enc1.isRight()) {
        if (++current_set >= 7) current_set = 6;
      } else if (enc1.isLeft()) {
        if (--current_set < 0) current_set = 0;
      }

      if (enc1.isRightH())
        changeSettings(1);
      else if (enc1.isLeftH())
        changeSettings(-1);

      changeSet();
    } else {
      backlOn();      // включить дисплей
    }
  }
}

// тут меняем номер помпы и настройки
void changeSettings(int increment) {
  if (current_set == 0) {
    current_pump += increment;
    if (current_pump > PUPM_AMOUNT - 1) current_pump = PUPM_AMOUNT - 1;
    if (current_pump < 0) current_pump = 0;
    s_to_hms(period_time[current_pump]);
    drawLabels();
  } else {
    if (current_set == 1 || current_set == 4) {
      thisH += increment;
    } else if (current_set == 2 || current_set == 5) {
      thisM += increment;
    } else if (current_set == 3 || current_set == 6) {
      thisS += increment;
    }
    if (thisS > 59) {
      thisS = 0;
      thisM++;
    }
    if (thisM > 59) {
      thisM = 0;
      thisH++;
    }
    if (thisS < 0) {
      if (thisM > 0) {
        thisS = 59;
        thisM--;
      } else thisS = 0;
    }
    if (thisM < 0) {
      if (thisH > 0) {
        thisM = 59;
        thisH--;
      } else thisM = 0;
    }
    if (thisH < 0) thisH = 0;
    if (current_set < 4) period_time[current_pump] = hms_to_s();
    else pumping_time[current_pump] = hms_to_s();
  }
}

// вывести название реле
void drawLabels() {
  lcd.setCursor(1, 0);
  lcd.print("                ");
  lcd.setCursor(1, 0);
  lcd.print(relayNames[current_pump]);
}

// изменение позиции стрелки и вывод данных
void changeSet() {
  switch (current_set) {
    case 0: drawArrow(0, 0); update_EEPROM();
      break;
    case 1: drawArrow(7, 1);
      break;
    case 2: drawArrow(10, 1);
      break;
    case 3: drawArrow(13, 1);
      break;
    case 4: drawArrow(7, 1);
      break;
    case 5: drawArrow(10, 1);
      break;
    case 6: drawArrow(13, 1);
      break;
  }
  lcd.setCursor(0, 1);
  if (current_set < 4) {
    lcd.print(L"ПАУЗА ");
    s_to_hms(period_time[current_pump]);
  }
  else {
    lcd.print(L"РАБОТА");
    s_to_hms(pumping_time[current_pump]);
  }
  lcd.setCursor(8, 1);
  if (thisH < 10) lcd.print(0);
  lcd.print(thisH);
  lcd.setCursor(11, 1);
  if (thisM < 10) lcd.print(0);
  lcd.print(thisM);
  lcd.setCursor(14, 1);
  if (thisS < 10) lcd.print(0);
  lcd.print(thisS);
}

// перевод секунд в ЧЧ:ММ:СС
void s_to_hms(uint32_t period) {
  thisH = floor((long)period / 3600);    // секунды в часы
  thisM = floor((period - (long)thisH * 3600) / 60);
  thisS = period - (long)thisH * 3600 - thisM * 60;
}

// перевод ЧЧ:ММ:СС в секунды
uint32_t hms_to_s() {
  return ((long)thisH * 3600 + thisM * 60 + thisS);
}

// отрисовка стрелки и двоеточий
void drawArrow(byte col, byte row) {
  lcd.setCursor(0, 0); lcd.print(" ");
  lcd.setCursor(7, 1); lcd.print(" ");
  lcd.setCursor(10, 1); lcd.print(":");
  lcd.setCursor(13, 1); lcd.print(":");
  lcd.setCursor(col, row); lcd.write(126);
}

// обновляем данные в памяти
void update_EEPROM() {
  scheduleConfigure(current_pump, period_time[current_pump], pumping_time[current_pump]);
  EEPROM.updateLong(8 * current_pump, period_time[current_pump]);
  EEPROM.updateLong(8 * current_pump + 4, pumping_time[current_pump]);
}
