---
slug: manual-watering
status: plan-ready
intent: clear
review_required: false
pending-action: user chooses execution or optional high-accuracy review
approach: manual group request with per-pump ownership, independent automatic channels, and an LCD workflow that preserves existing held-rotation editing
---

# Draft: manual-watering

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->

## Findings (cited - path:lines)

## Decisions (with rationale)

## Scope IN

## Scope OUT (Must NOT have)

## Open questions

## Approval gate
status: plan-ready
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->

## Grounded proposal (not an approved execution plan)

Classification: standard. No product files modified. Explicit planning request only.
No codegraph exploration tool exposed; read-only source exploration used.

### Components ledger

| id | outcome | status | evidence |
| --- | --- | --- | --- |
| execution | One running manual group with independent timer and per-pump ownership; unrelated automatic pumps keep running | active | src/main.cpp:178-207 |
| controls | Separate manual workflow for pump mask, duration, start/stop, return; retain original automatic editing | active | src/main.cpp:215-237; lib/GyverEncoder/src/GyverEncoder.h:55-67 |
| recovery-QA | RTC/EEPROM rules preserved, no manual resume after reboot, register/GPIO-level and encoder scenario coverage | active | src/rtc_schedule.cpp:141-168; .pio/qa/rtc-check.cjs |

### Verified findings

- PARALLEL=1 already gives independent automatic starts: include/config.h:11 and src/main.cpp:178-193.
- Automatic runtime currently shares pump_state and pump_timers; flowTick writes GPIO and scheduleStopped. Manual GPIO writes alone would be overwritten or misclassified: src/main.cpp:60-68,195-207.
- Main loop checks RTC before handling encoder/outputs; a clock fault stops all pumps and latches RTC error: src/main.cpp:140-164.
- A standalone isClick event is available; held rotation is already editing and must not become a page-switch gesture: GyverEncoder.cpp:111-125,137-187.
- Original startup hold resets settings; manual actions must not be triggered at boot: src/main.cpp:95-105.
- Automatic deadlines are persisted independently of millis; new record format is NOT required for this scope: src/rtc_schedule.cpp:14-23,105-168.
- Source research suggestion that pins 14-17 are invalid was rejected: installed Arduino standard/pins_arduino.h defines PIN_A0=14 through PIN_A3=17, consistent with current firmware.

### Proposed behavior

- Select any nonempty group of 1-14 pumps, including pumps with disabled auto mode.
- One common positive duration, frozen at submission; selected automatic runs are preempted and all selected pumps start manually in the same loop transition.
- Only one manual request running. A second request is rejected as busy; no hidden request queue.
- Other pumps continue their independent automatic schedules. Selected pumps cannot be driven by auto and manual simultaneously.
- Visible Stop stops only the manual group outputs. Leaving the manual screen does not cancel a submitted request.
- Manual state remains volatile. Reboot initializes all outputs off and does not resume a manual dose. RTC error stops auto and manual as it does today.
- Preserve diagram layout, relay, sw1 and all original wires. Do not add statistics, calendar pages, Wi-Fi, sensors or full old architecture.

### Proposed control flow

- Short click at automatic pump heading (current_set=0) opens an Auto/Manual selector. Existing ordinary/held rotation for automatic configuration remains unchanged.
- Manual: pump selection with rotation/click toggles; Next; common duration H/M/S; explicit Start confirmation.
- Running view displays state, selected count and remaining time; explicit Stop and Back actions. Back preserves the running request.
- No action from held-rotation release: GyverEncoder suppresses isClick after rotation; confirm this with GPIO-level QA.
- Empty mask and zero duration cannot start. Duration upper bound remains the current editable time range; final exact bound must be specified without silently changing auto formatting.

### Owner decisions approved (latest user message)

1. For a pump that is idle when manual starts, retain its existing automatic nextDue. Manual completion/Stop does not move it. If due passes during manual, that pump starts one overdue auto run after manual releases it.
2. For a pump already running automatically, preempt that automatic dose immediately and treat it as completed. Set its nextDue to interruption wall time + full configured pause, persist before manual energizing, then begin its manual timer. This exception intentionally replaces the older nextDue.
3. Other automatic pumps continue independently; no global waiting or suspension. Selected manual channels cannot auto-start until manual ends.
4. The user answered the two product forks following the concrete planning brief; this accepts the approach for plan creation only. No implementation authorized this turn.

No remaining owner decisions. Do not ask the same approval again. Write one executable plan, run mandatory gap analysis, then hand off without product-code changes.

### Proposed implementation order

1. Explicit per-pump Idle/Auto/Manual ownership and runtime deadlines; preserve automatic behavior first.
2. Manual group lifecycle: selection validation, running/stop, selected-channel arbitration and owner-approved schedule rule.
3. LCD/encoder manual workflow alongside original auto editor, with first wake gesture consumed and no accidental starts.
4. Agent-executed QA and documentation: both RTC profiles, encoder GPIO sequences, overlapping auto/manual outputs, independent deadlines, failed RTC, restart and interrupted EEPROM writes.

Verification strategy: tests-after on real compiled AVR machine code using existing register-level RTC/GPIO runner, extending temporary .pio/qa fixtures without introducing a new permanent test framework. Both PlatformIO profiles must build without new application warnings. Graphical Wokwi evidence is distinct and must not be claimed from CPU emulation; use it when the application-control surface works, otherwise report the exact limitation.

### Approval gate state

Approved for plan creation by the user answering both owner decisions after the brief. Next action: complete .omo/plans/manual-watering.md, integrate Metis, structural self-check, deliver plan. Execution remains separately authorized.

## Completed planning record

Plan: .omo/plans/manual-watering.md
Plan SHA256: 13101800ce8f1d272c925c7b238a89dcbfe85a7153bcb28dec144bfe48677070
Shape: 6 numbered implementation todos in 2 waves; 4 F-numbered final-verification todos.
Structural check PASS: all 8 scaffold headers in order; implementation rows in Todos,
final rows in Final verification wave; every implementation task has References,
Acceptance, QA and Commit=N; no fill/title placeholders.
Mandatory Metis agent /root/manual_plan_gaps finished: 13 gaps found in draft/skeleton.
All integrated into the completed plan: explicit duration bound, 16x2 state table,
commit-before-output ordering, scheduleInterrupted API, same-tick ownership priority,
encoder/backlight consumption, boot/RTC teardown, actual populated todos, fresh-checkout
QA recreation, compiled-HEX assertions, AUTO gesture regression, pump_control ownership,
manual_ui ownership. No remaining owner questions; no high-accuracy review requested.
No product files changed in planning turns. Executor must re-read the plan and current
source before edits. Implementation not started. Next: choose execution or optional review.
