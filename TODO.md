# TODO

Period-accurate app ideas, grouped by what they need.

## Built from what's already there

- [x] **Schedule / Agenda:** a day view with time slots, plus a week strip in the header, like the Wizard's Schedule.
- [ ] **To Do:** priority and done checkboxes. The icon sets already have `checkbox_done_todo` and friends.
- [ ] **Anniversary:** birthdays with "in 12 days" countdowns. It's on the ZQ-770's own main menu ("Birthday").
- [ ] **Conversion:** units and currency with editable rates, like the Wizard's Conversion app.
- [x] **World Clock:** a dotted pixel world map with a day/night shadow and city times, like Psion's World app.
  - Convert the vector map in `badgeware/tufty2350/firmware/assets/world.geo.json` (per-country polygons in degrees, 215KB) to a 1-bit or 2-bit bitmap offline, sized for the panel. statsbadge's `badge_app/worldmap.py` has the equirectangular projection, the aspect correction and night-side drawing to borrow.
- [ ] **Data:** a card-file database with fields you define yourself, like Psion Data. It's mostly the existing Form plus List.
- [ ] **Secret memos:** password-locked notes with a simple cipher, like the Wizard's "Secret" mode.
- [ ] **Biorhythm:** three sine curves in three grey levels. Late-90s organiser software exactly.
- [x] **Char Map:** a browser for all 19 icon sets and the Sins glyphs, handy for app authors.
- [x] **More games:** Reversi, Mastermind, Hangman, Sokoban, and Solitaire using the card icons in `boardgames`.

## Needs a small host addition

- [x] **Beeper:** an SDL square-wave "piezo". It unlocks an alarm clock, key clicks and a stopwatch or timer that beeps.
- [x] **Tone dialer:** Tel dials numbers as DTMF tones through the beeper, as the real Wizards did.
- [x] **Background alarms:** a scheduler that fires while another app is open, like EPOC's alarm server.

## Bigger

- [ ] **WZD import:** read Sharp's `.wzd` add-ins. They're a tagged text container (`<SHARP WZD DATA>`, `<DATA TYPE>`, `<TITLE>`, `<CATEGORY>`, `<DESCRIPTION>`, `<DATA>`) wrapping "Sharp Download Data V1.0" CSV, with field codes per type (Memo: `TTL1`, `MEM1`, `DATE`...; Schedule: `TIM1`, `TIM2`, `ALRM`, `SRPT`...). The MEMO and SCHEDULE ones (holidays, paper sizes, dialling codes) map straight onto Memo and Schedule. Source: global.sharp ZQ-700 downloads.
- [ ] **Sharp BASIC add-ins:** `DATA TYPE` `BASIC` files (Biorhythm, Pegs, CSM_Calc) carry `<BIN>` tokenised Sharp pocket-computer BASIC: 2-byte line number, length byte, `0xFE`-prefixed tokens, `*LABEL`s, and code that assumes a 239px-wide screen. A detokeniser plus a small interpreter could run the originals.
- [ ] **Secret and Autorun:** the rest of the firmware Options menu. A password gates secret-flagged entries, with a lock organiser option. Autorun starts a program at power on.

- [x] **Program editor ("My Programs"):** write and run Python apps on the device itself, like OPL's Program editor on the Psion. The REPL plumbing already exists.
- [ ] **Infrared beaming:** send memos and contacts between two Pocket windows over localhost UDP, styled as IrDA with a "Receiving..." dialog.
- [ ] **PC Sync:** mirror memos and Tel entries to a folder on the Mac, like the ZQ-770's PC SYNC key.
- [ ] **Sheet:** a tiny spreadsheet with a cell grid and formulas, like Psion Sheet. It stretches the SDK well at 239x80.
