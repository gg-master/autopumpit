#pragma once

#define LCD_BACKL 1         // автоотключение подсветки дисплея (1 - разрешить) 
#define BACKL_TOUT 60       // таймаут отключения дисплея, секунды
#define ENCODER_TYPE 1      // тип энкодера (0 или 1). Если энкодер работает некорректно (пропуск шагов), смените тип
#define ENC_REVERSE 1       // 1 - инвертировать энкодер, 0 - нет
#define DRIVER_VERSION 1    // 0 - маркировка драйвера дисплея кончается на 4АТ, 1 - на 4Т
#define PUPM_AMOUNT 14       // количество помп, подключенных через реле/мосфет
#define START_PIN 4         // подключены начиная с пина
#define SWITCH_LEVEL 1      // Wokwi: реле npn активно по HIGH; для реле с активным LOW поставить 0
#define PARALLEL 1          // 1 - параллельный полив, 0 - полив в порядке очереди
#define TIMER_START 1       // 1 - отсчёт периода с момента ВЫКЛЮЧЕНИЯ помпы, 0 - с момента ВКЛЮЧЕНИЯ помпы

#define CLK 3
#define DT 2
#define SW 0


// Default profile: DS1307 in Wokwi. uno-ds3231 selects the physical DS3231.
#ifndef USE_DS3231
#define USE_DS3231 0
#endif
