# DRISHTI prototype — STATUS

**Read this first. It is the single source of truth for where the build is.**

- Design (approved 2026-09-25): `docs/specs/2026-09-25-drishti-prototype-design.md`
- Milestone task plans: `docs/plans/`
- Old research build (read-only source for ported code and raw data): `~/saakshya`
  (snapshot commit `abf2da4`)

## >>> RESUME HERE <<<

**Current milestone: M0 — Foundations + Statistical agent (target 30 Sept 2026).**

Done:
- 2026-09-25: design approved; repo created; old repo snapshot-committed.

Next:
- Build `docs/plans/M0-foundations-statistical.md`, starting at Task 1 (hosting spike).

## Milestones

| | Target | State |
|---|---|---|
| M0 Foundations + Statistical agent | 30 Sept | in progress |
| M1 Duplicate Project agent | ~7 Oct | not started |
| M2 Image Reuse agent | ~17 Oct | not started |
| M3 Site Progress agent (GPS) | ~31 Oct | not started |
| M4 Full loop (fusion, review, decisions) | ~15 Nov | not started |
| M5 Finale polish | Nov–Dec | not started |

## Guardrails (from the user — never break)

- Exactly the deck's pipeline and four agents. No new agents. No satellite anything.
- GPS/location validation lives inside Site Progress and Image Reuse.
- Free tiers only for now; paid Gemini is a switch, not a default.
- `main` is always the demoable live link; host at every milestone.
- The user is non-technical: report in plain words, outcome first.

## Live links

- Production: (not deployed yet)
