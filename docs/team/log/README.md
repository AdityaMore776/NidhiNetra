# Progress log

**One file per work session, never edited afterwards.** This is how every teammate's AI knows what
everyone else did. Separate files mean two people logging at once never clash.

- **Name:** `YYYY-MM-DD-HHMM-<github-user>-<task>.md` (IST), e.g. `2026-10-02-1830-simran-T103.md`.
  Files sort by time, so the newest are at the bottom of the folder listing.
- **Create one:** `python scripts/team/new_log.py T103 "read sanction dates from certificates"`
  (fills in the template with your name, time and branch). Then fill in every heading.
- **Read before you start:** the newest 5–10 files (`python scripts/team/sync.py` lists them).
- **Required:** CI rejects a pull request that adds no file here.
- **Public:** this repo is public. Refer to works by work ID; never write people's names, phone numbers,
  account numbers, passwords or keys.
- **Tasks that aren't code** (research, deck, a decision): log them too, with task `T000` if there is no ID.
