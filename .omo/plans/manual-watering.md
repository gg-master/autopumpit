# manual-watering - Work Plan

## TL;DR (For humans)
**What you'll get:** Ручной запуск выбранных помп на общее заданное время с кнопкой остановки; остальные автоматические помпы продолжают работать независимо.

**Why this approach:** Один исполнитель управляет каждым каналом и различает автоматический и ручной полив. Это исключает конфликт таймеров и сохраняет уже работающие часы и восстановление питания.

**What it will NOT do:** Статистика, новые календарные режимы, сеть и датчики не добавляются. Схема и привычное редактирование автоматических интервалов сохраняются.

**Effort:** Medium
**Risk:** Medium — пересечение таймеров одного канала, сохранение срока при прерывании и управление на экране16×2.
**Decisions to sanity-check:** Срок неработающей выбранной помпы сохраняется. У уже работающей автоматически помпы доза завершается при ручном старте, следующая пауза отсчитывается от прерывания. Конец ручного полива срок больше не сдвигает.

Your next move: План готов к выполнению после отдельной команды запуска; по желанию перед этим можно заказать углублённую проверку плана.

---

> TL;DR (machine): Medium; 6 implementation tasks / 2 sequential waves + 4 read-only final verifiers; independent auto/manual ownership, interruption persistence, 16x2 UI, both RTC profiles.

## Scope
### Must have
- Разовый ручной запуск любой непустой группы из 1–14 помп, включая помпы с выключенной автоматикой. Одна общая длительность 00:00:01–99:59:59 (1–359999 секунд), uint32_t; параметры фиксируются при подтверждении.
- PARALLEL=1 сохраняется: все невыбранные автоматические помпы продолжают независимо работать и запускаться по своим срокам.
- Для выбранной Idle-помпы старый nextDue не меняется. Для выбранной Auto-помпы текущий автополив завершается досрочно: nextDue := RTC-время прерывания + полная настроенная пауза. Это единственное исключение из сохранения прежнего срока. При отключённой автоматике nextDue остаётся 0.
- Прерывание назначает полную паузу независимо от TIMER_START; обычные автоматические циклы сохраняют прежнюю семантику TIMER_START.
- Транзакция старта: проверить и зафиксировать запрос -> выключить выбранные Auto-выходы -> сохранить новые сроки всех прерванных Auto-помп и дождаться EEPROM commit -> назначить всем выбранным владельца Manual -> взять общий millis() старта -> включить выбранную группу. Не менять сроки выбранных Idle-помп. Одновременность означает один проход управления, без последовательной отработки длительностей.
- Пока канал Manual, автоматический start/stop этого канала запрещён. По таймеру или Stop: выключить только ручную группу, освободить её каналы; НЕ вызывать RTC start/stop и НЕ сдвигать nextDue. Затем штатная автоматика может выполнить один просроченный запуск каждого освободившегося канала, включая только что остановленный вручную.
- Один ручной запуск за раз; повторный запрос во время работы возвращает Busy без изменений. Ожидания завершения автополива и очереди ручных запросов нет.
- Back во время работы не останавливает запрос; повторный вход показывает работающий запрос. Stop не отключает автоматическое расписание: просроченная автоматика может включить канал снова после освобождения.
- Ручные маска/время/состояние существуют только в RAM. Перезапуск не возобновляет ручную дозу. Сохранённый после прерывания Auto новый срок восстанавливается обычным RTC-кодом. При ошибке RTC — общий all-off и очистка ручного состояния до перезапуска, как сейчас.
- Сохранить существующий редактор AUTO, кнопку/переключатель Wokwi, все провода и расположение схемы; новая навигация использует только имеющийся энкодер.
### Must NOT have (guardrails, anti-slop, scope boundaries)
- Не переносить старую модульную архитектуру Auto-Pumps; не добавлять статистику, календарное меню, фиксированные часы полива, Wi-Fi, датчики, ОС/потоки или новые аппаратные органы управления.
- Не менять EEPROM layout/version/legacy offsets и не сохранять ручной запрос в EEPROM. Не обнулять nextDue из-за обычного ручного завершения или Stop.
- Не блокировать остальные каналы глобальным manualActive/now_pumping. Не использовать delay для длительности, Arduino String или heap-контейнеры в новом коде.
- Не исправлять попутно старый AUTO-редактор, библиотеки, полярность реле или схемы; не заменять проект полной переработкой.
- Не коммитить, не создавать ветку/PR и не сбрасывать рабочее дерево. Исходные файлы сейчас не закоммичены: перечитать перед правкой и сохранять пользовательские изменения.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after, машинный код AVR на существующем подходе AVR8js; новый постоянный тестовый framework не вводить.
- Обязательные сборки: `python -m platformio run -e uno -e uno-ds3231`. Обе должны завершиться 0, без новых предупреждений приложения; прежние GyverEncoder/EEPROMex warnings описать отдельно.
- `.pio/qa` игнорируется Git и может отсутствовать. Создать временный стенд, если нужно: `npm.cmd install --prefix .pio/qa avr8js@0.21.0 intel-hex@0.2.0`. Не предполагать наличие старого rtc-check.cjs в чистом checkout.
- Создать `.pio/qa/manual-check.cjs`: загрузка реального HEX, CPU/Timer0/GPIO/EEPROM/TWI и регистров DS1307/DS3231; адреса символов извлекать PlatformIO `avr-nm -C` из соответствующего ELF. Не реализовывать копию алгоритма полива в JS.
- Для API-проверок до появления UI создать временный `.pio/qa/platformio.ini`, src_dir=.pio/qa/driver, include_dir=include, lib_dir=lib, build_dir=.pio/qa/build; те же AVR platform/board/framework и pinned RTClib/BusIO, что в основном platformio.ini. Драйвер включает реальные rtc_schedule.cpp и pump_control.cpp, когда он создан, ровно по одному разу; экспортирует команды и результаты в volatile RAM для CJS. Это тестовый драйвер, не изменение production firmware.
- API-команды: `python -m platformio run -c .pio/qa/platformio.ini -e qa-ds1307 -e qa-ds3231`; `node .pio/qa/manual-check.cjs --suite <rtc-interruption|automatic|manual> --env <qa-ds1307|qa-ds3231>`.
- После UI: `node .pio/qa/manual-check.cjs --suite full --env uno` и `--env uno-ds3231`; реальные входные последовательности D0/D2/D3, наблюдение GPIO, EEPROM и LCD-потока через PCF8574 на 0x27. Добавить декодирование DDRAM/команд для проверки двух строк по 16 колонок; не выдавать его за визуальный Wokwi.
- Подсветка: первый click/turn при выключенной подсветке только будит экран; он не открывает меню, не запускает/останавливает помпы. Каждый следующий вход потребляется ровно один раз.
- Перезапуск: новый CPU с прежней EEPROM и продвинутым RTC, millis начинается заново. Дополнительно RTC-disconnect, потеря хода, неполная запись, millis rollover.
- Подтвердить 14 выходов, крайние маски/длительности, перекрытие auto/manual, невыбранные каналы, сохранение сроков Idle, перенос срока Auto, общие ручные длительности, Stop/Back/Busy, ошибочные запросы и безопасный boot.
- Графический Wokwi запускать через доступное управление приложением. Если поверхность по-прежнему не инициализируется, записать точную ошибку отдельно; не заявлять визуальную проверку. Функциональное доказательство машинным кодом и ограничение графической проверки разделять.
- Evidence: .omo/evidence/manual-watering/task-N-*.txt; итоговый отчёт .omo/evidence/manual-watering/summary.md. Временный стенд в .pio/qa, без инструментирования production кода; документировать путь воспроизведения в docs/manual.md.

## Execution strategy
### Parallel execution waves
- Wave 1, последовательно: 1 RTC API -> 2 единый исполнитель помп -> 3 ручной жизненный цикл. Все три меняют связанные контракты; не делить их между одновременными редакторами.
- Wave 2: 4 LCD/энкодер -> 5 полная интеграционная QA -> 6 документация и итоговые артефакты. Исправления проверять до перехода дальше; не расширять охват.
- Независимые финальные проверки F1–F4 запускаются параллельно после выполнения 1–6. Руководитель интегрирует их фактические доказательства.
### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | — | 2,3 | — |
| 2 | 1 | 3,4 | — |
| 3 | 1,2 | 4,5 | — |
| 4 | 2,3 | 5 | — |
| 5 | 1–4 | 6 | — |
| 6 | 5 | F1–F4 | — |

## Todos
> Implementation + Test = ONE todo. Never separate.

- [ ] 1. Добавить узкую операцию завершения прерванного автополива
  What to do / Must NOT do: В include/rtc_schedule.h и src/rtc_schedule.cpp добавить scheduleInterrupted(uint8_t pump, uint32_t pause, uint32_t run). При ненулевых pause/run записать nextDue=wallNow+pause, иначе 0. Использовать существующий saveRecord и его eeprom_busy_wait; не менять схему, не вызывать scheduleConfigure (он пропускает неизменённые настройки), не учитывать TIMER_START в этой операции. Все прерванные каналы одного запроса получают время одного текущего чтения RTC. Создать временный API-драйвер/стенд из Verification strategy.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2,3
  References (executor has NO interview context - be exhaustive): include/rtc_schedule.h:5; src/rtc_schedule.cpp:14 (layout), :66 (saveRecord), :105 (restore), :146 (configure), :157 (start), :163 (stop); platformio.ini; .gitignore:1; .omo/drafts/manual-watering.md (latest approved decisions).
  Acceptance criteria (agent-executable): обе основные сборки 0; API-драйвер проверяет точный now+pause, disabled->0 и восстановление нового срока после CPU reboot; обычные configure/start/stop сохраняют прежнее поведение. Целая предыдущая копия переживает оборванную новую запись.
  QA scenarios (name the exact tool + invocation): `node .pio/qa/manual-check.cjs --suite rtc-interruption --env qa-ds1307` и qa-ds3231; happy: прерывание в известную RTC-секунду, reboot до нового срока; failure: обрыв записи перед маркером/CRC, восстановление предыдущей целой копии. Evidence .omo/evidence/manual-watering/task-1-rtc.txt.
  Commit: N | User did not request commits.

- [ ] 2. Выделить единственного владельца GPIO и состояний помп
  What to do / Must NOT do: Добавить include/pump_control.h и src/pump_control.cpp; перенести только pump_pins/pump_timers/pump_state, periodTick, flowTick и all-off из main.cpp. Вместо общего boolean использовать per-pump enum Idle/Auto/Manual. Модуль принимает ссылки/указатели на существующие массивы pause/run, не дублирует конфигурацию. Он один пишет GPIO помп; LCD/энкодер остаются вне него. API: begin с настройками (выходы OFF, исполнитель disabled), enable после scheduleBegin, tick, stopAll (OFF+disabled+очистка volatile состояния). Сначала сохранить только существующее AUTO-поведение; состояние Manual зарезервировано до todo3. tick безопасен до enable. PARALLEL=1 остаётся независимым; если сохранён старый guard PARALLEL=0, вычислять занятость по per-pump owners, а не ложному глобальному флагу. Не менять работу авто-редактора или другие пины.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3,4
  References (executor has NO interview context - be exhaustive): src/main.cpp:60–83 (перемещаемые поля/инициализация), :119–164 (RTC gate/all-off), :178–207 (автоциклы); include/config.h:8–16; include/channel_names.h; README.md (A0=14…A3=17); src/rtc_schedule.cpp:157–168.
  Acceptance criteria (agent-executable): все 14 выходов выключены до enable/после stopAll; прежняя независимая автоматика и RTC recovery проходят на обоих профилях; в main/manual_ui нет digitalWrite для помп; общие таймеры не блокируют другие каналы.
  QA scenarios (name the exact tool + invocation): `node .pio/qa/manual-check.cjs --suite automatic --env qa-ds1307` и qa-ds3231; happy: 14 перекрывающихся запусков и три разнесённых старта/остановки; failure: tick до enable, RTC отказ и CPU reboot — все выходы безопасны. Evidence .omo/evidence/manual-watering/task-2-runtime.txt.
  Commit: N | User did not request commits.

- [ ] 3. Реализовать ручной групповой запуск с одобренным прерыванием Auto
  What to do / Must NOT do: В pump_control добавить requestManual(mask, seconds), stopManual и read-only ManualStatus (running, mask, remainingSeconds). Результаты Started/Busy/InvalidSelection/InvalidDuration/Unavailable. Маска uint16_t, только младшие PUPM_AMOUNT бит, диапазон 1..359999 секунд; отклонять запрос без эффектов, если executor disabled или уже работает ручная группа. Заморозить параметры. Следовать точному порядку транзакции из Scope: OFF выбранных Auto, scheduleInterrupted для каждого, затем Manual owners, общий millis и ON группы. Idle nextDue не трогать. Авто tick никогда не стартует/останавливает Manual-канал; невыбранные каналы не блокировать. При естественном завершении/Stop отключить группу и освободить её без RTC-записей; на ближайшем авто tick разрешить один overdue запуск. Все manual-поля очищаются stopAll/boot. Использовать wrap-safe elapsed subtraction, максимум 359999000 мс < 2^31, remaining округлять вверх до секунды с проверкой elapsed>=duration перед вычитанием. Не добавлять waiting/pending фазу, очередь, продление или второй ручной запрос.
  Parallelization: Wave 1 | Blocked by: 1,2 | Blocks: 4,5
  References (executor has NO interview context - be exhaustive): .omo/drafts/manual-watering.md (approved two owner decisions); include/pump_control.h и src/pump_control.cpp из todo2; include/rtc_schedule.h и src/rtc_schedule.cpp из todo1; src/main.cpp:140–164; include/config.h:11–12.
  Acceptance criteria (agent-executable): Idle due неизменен на start/end/Stop; Auto due становится interruption+pause до первого Manual HIGH; manual длительность не использует run из автонастроек; другие auto продолжают; Busy/invalid не меняют GPIO/EEPROM; manual не возобновляется после reboot. Если due наступает в тот же tick, подтверждённый ручной запрос имеет приоритет над новым автостартом. Уже завершившийся по времени Auto сначала штатно завершается, без лишнего прерывания.
  QA scenarios (name the exact tool + invocation): `node .pio/qa/manual-check.cjs --suite manual --env qa-ds1307` и qa-ds3231; happy: mixed Idle+Auto группа, прерывание в 12:10/пауза30мин -> due12:40, Manual дольше паузы -> ровно один auto после освобождения; failure: mask0/бит вне14, duration0/>359999, Busy, RTC loss, reboot/torn interruption write, millis rollover. Наблюдать порядок EEPROM commit/OFF/ON, не только итоговые переменные. Evidence .omo/evidence/manual-watering/task-3-manual.txt.
  Commit: N | User did not request commits.

- [ ] 4. Добавить отдельный ручной экран без изменения привычного AUTO-редактора
  What to do / Must NOT do: Добавить include/manual_ui.h и src/manual_ui.cpp — только UI-состояния и черновик выбора/времени; main.cpp остаётся оркестратором энкодера, подсветки и RTC. Все start/stop через pump_control. Порядок loop: RTC validation/all-off -> завершение истёкших runtime-таймеров -> один входной event/UI (manual request до новых автостартов) -> новые auto starts -> обновление отображения. Не запускать две обработки одного event и не опрашивать enc.tick дважды. Не использовать isHolded для перехода экранов: удержание нужно старому редактированию и sw1.
  Parallelization: Wave 2 | Blocked by: 2,3 | Blocks: 5
  References (executor has NO interview context - be exhaustive): src/main.cpp:140–151 (loop), :166–176 (backlight), :215–353 (AUTO input/drawing/save); lib/GyverEncoder/src/GyverEncoder.h:43–67; lib/GyverEncoder/src/GyverEncoder.cpp:111–125 и :137–187; lib/LCD_1602_RUS/src/LCD_1602_RUS.h; diagram.json (sw1); include/channel_names.h.
  Acceptance criteria (agent-executable): точная таблица ниже реализована; held-turn AUTO и release после него не открывают меню. AUTO настройки не теряются/не сохраняются самопроизвольно из-за переключения; selector открывается только из current_set=0, где старые изменения уже сохранены. При выключенной подсветке первый click/turn только будит экран. Каждый текст занимает <=16 колонок, строки дополняются пробелами для стирания старых символов; countdown обновляется без блокировки управления. Черновик Manual RAM-only; default duration5с, mask0, сброс при новом неподтверждённом входе. Возврат при активном запросе всегда показывает Running.
  UI state table:
  - AUTO: прежние rotate/held-rotate и поля0..6; standalone click только при field0 -> Selector. В других полях click ничего не делает.
  - Selector: rotate выбирает AUTO/MANUAL, click входит; AUTO возвращает прежний current_pump/field0, MANUAL открывает Running при active иначе Pumps.
  - Pumps: курсор Pump1..PumpN, Next, Back; rotate перемещает, click на помпе toggles, Next при mask!=0 -> Duration, иначе короткое сообщение без запроса; Back -> Selector. Строка0 — текущее имя, обрезанное до16, строка1 — отметка выбора и count; Next/Back отображаются отдельно как элементы списка.
  - Duration: курсор H/M/S/Next/Back; rotate перемещает, held-rotate меняет только число под курсором с clamp H0..99/M,S0..59; standalone click на числовом поле переводит к следующему, Next с положительным временем -> Confirm, Back -> Pumps. Нулевое время не подтверждается. Строки: `Manual 03 pumps` и время HH:MM:SS со стрелкой либо строка действия Next/Back.
  - Confirm: rotate Start/Back, click Start -> один requestManual и Running; Back -> Duration; ошибки показываются в пределах16 символов без повторной отправки. Строки `Start 03 pumps?` и `>Start     Back` с актуальной стрелкой.
  - Running: строка0 `M03 00:00:05` (count и remaining, формат HH:MM:SS), строка1 `>Stop      Back`; rotate выбирает Stop/Back; click Stop -> stopManual и Result; Back -> AUTO field0 без отмены; естественный конец -> Result только если экран ещё Running. При возвращении из AUTO запрос не дублировать.
  - Result: строка0 `Manual done` либо `Manual stopped`, строка1 `>Back`; click -> AUTO field0. Наличие Result не блокирует automatic tick. Старую маску/время можно использовать лишь для отображения результата, не для скрытого повторного запуска.
  QA scenarios (name the exact tool + invocation): `node .pio/qa/manual-check.cjs --suite full --env uno` и uno-ds3231; happy: GPIO-энкодером выбрать1,3,14 -> задать5с -> Confirm -> Back -> reopen Running -> Stop, другие auto продолжают; failure: пустая маска/0с, held-release не click, wake не Start/Stop, RTC error не допускает manual. Проверить LCD DDRAM <=16, отсутствие хвостов, countdown и обе полярности turn. Evidence .omo/evidence/manual-watering/task-4-ui.txt.
  Commit: N | User did not request commits.

- [ ] 5. Прогнать полную регрессию на обоих RTC и независимых выходах
  What to do / Must NOT do: Довести временный full-стенд до воспроизводимого запуска из чистой .pio/qa; проверить production HEX каждого профиля, а не только API-драйвер. Сохранить commands/exit codes/hashes/наблюдения. Добавить все граничные и совместные сценарии из Verification strategy; дефекты исправлять в минимальном владельце, без расширения функций.
  Parallelization: Wave 2 | Blocked by: 1–4 | Blocks: 6
  References (executor has NO interview context - be exhaustive): docs/rtc.md; docs/verification.md (предыдущие 22 проверки); platformio.ini; .pio/qa/rtc-check.cjs если присутствует (не обязательная зависимость); production modules из1–4; `.omo/plans/manual-watering.md` Scope/UI state table.
  Acceptance criteria (agent-executable): основные и QA сборки 0; оба production full прогона 0; доказаны 14 каналов, millis rollover, 99:59:59 без переполнения, stop/back/busy, отключение/возврат питания и RTC; нет новых application warnings, Flash<=32256 и RAM<2048 с проверкой остатка для stack/RTClib. Не скрывать переполнение или менять тестовые ожидания для обхода ошибки. Допуск времени учитывает RTC-секунды и существующую синхронную EEPROM-запись, но не допускает ожидание полной длительности другой помпы.
  QA scenarios (name the exact tool + invocation): `python -m platformio run -e uno -e uno-ds3231`; `node .pio/qa/manual-check.cjs --suite full --env uno` и uno-ds3231; happy: idle due stays fixed, Auto interruption rebased, unselected autos overlap; failure: потеря питания на каждой границе commit/Manual-on, RTC исчезает во время Manual, ошибочные параметры и переполнение срока manual через millis rollover. Wokwi — существующий relay1/sw1, запуск и экранная проверка при доступном инструменте; иначе точная limitation, без выдуманного PASS. Evidence .omo/evidence/manual-watering/task-5-regression.txt.
  Commit: N | User did not request commits.

- [ ] 6. Документировать итоговое поведение и собрать доказательства
  What to do / Must NOT do: Обновить README.md, docs/rtc.md, docs/verification.md; добавить docs/manual.md с gestures, state flow, условиями1/2 и примерами, Stop/Back, RTC/reboot и pinned QA recreation commands. Указать, что Stop не выключает расписание и overdue auto может стартовать сразу. Не описывать неподтверждённый визуальный/аппаратный результат как проверенный. Проверить неизменность diagram.json и исходных библиотек, отсутствие временного production инструментирования. Не удалять пользовательские файлы и не повторять ранее отклонённую очистку .pio; новые QA артефакты оставлять в игнорируемом кэше с указанием пути.
  Parallelization: Wave 2 | Blocked by: 5 | Blocks: F1–F4
  References (executor has NO interview context - be exhaustive): README.md; docs/rtc.md; docs/verification.md; docs/upstream.md; diagram.json; .gitignore; .omo/evidence/manual-watering/task-1..5-*.
  Acceptance criteria (agent-executable): документация совпадает с наблюдаемыми условиями/управлением; 6 задач подтверждены свежими артефактами против одного финального кода; исходная схема/библиотеки не затронуты. В итоговом сообщении указать действия, обе сборки, QA, ограничения Wokwi и путь инструкции.
  QA scenarios (name the exact tool + invocation): повторить основные сборки и full прогоны только если после todo5 менялся код; `git diff --check` и SHA256 по итоговым HEX/diagram; happy: инструкции соответствуют GPIO-сценарию выбора/старта/Stop; failure: явно перечислить любой отсутствующий GUI/hardware evidence. Evidence .omo/evidence/manual-watering/task-6-handoff.txt.
  Commit: N | User did not request commits.

## Final verification wave
> Независимые read-only проверки после1–6, можно параллельно; все findings закрываются до итогового PASS. Результат не приравнивается к пользовательскому разрешению реализации.
- [ ] F1. Plan compliance audit
  Проверить условия1/2 по фактическому коду и EEPROM/GPIO timeline, сохранение независимой автоматики, отсутствие ожидания/статистики. Evidence .omo/evidence/manual-watering/f1-compliance.md.
- [ ] F2. Code quality review
  Проверить единственного владельца GPIO, per-pump owners, wrap-safe таймеры, границы mask/time, отсутствие новых heap/framework и новых предупреждений. Evidence .omo/evidence/manual-watering/f2-quality.md.
- [ ] F3. Real manual QA
  Повторить реальную последовательность GPIO-энкодера на production HEX обоих RTC, прочесть LCD/выходы и подтвердить start/back/stop/RTC-off/reboot; визуальный Wokwi свидетельствовать отдельно и не подменять эмуляцией. Evidence .omo/evidence/manual-watering/f3-qa.md.
- [ ] F4. Scope fidelity
  Сравнить заявленное и реализованное: только ручной полив и необходимое взаимодействие с авто, без старого большого проекта; diagram/библиотеки не изменены, пользовательские файлы сохранены. Evidence .omo/evidence/manual-watering/f4-scope.md.

## Commit strategy
Коммиты, ветки, PR и публикация не запрошены. Все Commit=N. Не выполнять git reset/clean/checkout для очистки: рабочее дерево содержит пользовательскую основу без коммитов.

## Success criteria
- Выполняются обе последние пользовательские политики, включая исключение прерванного Auto и неизменный срок Idle.
- Выбор1–14, common manual duration, Start/Stop/Back работают на существующем LCD/энкодере, с сохранением AUTO-редактирования и sw1.
- Нет одновременных владельцев одного GPIO; другие auto помпы не блокируются, собственные timers независимы.
- Boot/RTC fault безопасны; manual не возобновляется; сохранение нового срока прерванного Auto переживает restart и обрыв записи.
- Обе сборки/машинные проверки проходят, F1–F4 без незакрытых продуктовых блокеров; ограничения GUI/hardware названы явно.
- Пользователь получает инструкции и проверяемый результат без лишних функций, коммитов и повторного интервью по уже выбранным правилам.

