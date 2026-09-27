# How Team NeuralNexus works on DRISHTI

**For the humans on the team.** Your AI reads [`AGENTS.md`](../../AGENTS.md) and does the git work; this page
explains what it's doing and the few things only you can do. No coding knowledge needed.

---

## The idea in one minute

Think of the project as a shared kitchen with one serving counter (the live website).

- **main** is the serving counter. Whatever is on main is what the judges see at
  https://drishti-lyart.vercel.app. Nobody cooks directly on the counter.
- **A branch** is your own chopping board: a private copy of the code where your AI works on one task.
- **A pull request (PR)** is carrying the finished dish to the counter and asking "OK to serve?". GitHub
  runs **automatic checks (CI)** on it: tests, a privacy scan, "did you write the log entry?". Red = fix
  first; green = a teammate glances at it and it's merged. Merging updates the live site within minutes.
- **Issues** are the order tickets on the wall: one ticket per task (T101, T102, …). Taking a ticket
  ("assigning" it to yourself) tells everyone *I'm cooking this*, so two people never make the same dish.
- **The log** (`docs/team/log/`) is the kitchen diary: after every session your AI writes what it did and
  what comes next, so anyone's AI can pick up where it stopped.
- **The plan** (`docs/team/TASKS.md`) is the recipe book: every task, how to do it, and when it counts as done.

**The golden rule: if it isn't written in the repo or on an issue, the AIs don't know it.** Chat on WhatsApp
as much as you like, but a decision only counts once it's in an issue comment or a log entry.

---

## One-time setup (about 30 minutes)

1. **GitHub account** → send your username to the owner (@AdityaMore776), who adds you as a collaborator.
   Accept the email invite (or open https://github.com/AdityaMore776/drishti/invitations).
2. **Install the tools.** On Windows, open PowerShell and run:
   ```powershell
   winget install --id Git.Git -e
   winget install --id GitHub.cli -e
   winget install --id Python.Python.3.12 -e
   winget install --id OpenJS.NodeJS.LTS -e
   ```
   Close and reopen PowerShell afterwards. (Mac: `brew install git gh python@3.12 node`.)
3. **Log in to GitHub from the terminal:** `gh auth login` → GitHub.com → HTTPS → "Login with a web browser".
   Then tell git who you are:
   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "the-email-on-your-github-account"
   ```
4. **Download the project:**
   ```powershell
   cd $HOME
   gh repo clone AdityaMore776/drishti
   cd drishti
   ```
5. **Get the private data pack** from the team's Google Drive folder (the owner shares it with you) and unpack
   it: `python scripts/team/install_pack.py "$HOME\Downloads\DRISHTI-team-pack.zip"`.
   Details: [`DATA-PACK.md`](DATA-PACK.md). *Never upload these files anywhere else.*
6. **Install your AI tool** (Claude Code, Codex, Cursor, Gemini CLI, Copilot, …) and open it **in the
   `drishti` folder**. Then say the start sentence below. It sets up the rest (Python and web packages) by
   following [`docs/SETUP.md`](../SETUP.md).

---

## Every session: two sentences

**Start:**
> Read AGENTS.md and start a DRISHTI session.

Your AI will pull everyone's latest work, read the recent log, show you what's free, claim a task for you,
and tell you its plan. Answer its questions; say yes or no to what it proposes.

**End (always, even if the task isn't finished):**
> Wrap up the session as AGENTS.md section 5 says.

It writes the log entry, saves (pushes) the work, and tells you what's left.

Useful in between:
- "What is everyone working on?" → it runs `python scripts/team/sync.py`.
- "I want to do T304." → it checks T304 is free and its dependencies are done, then claims it.
- "Review PR #12." → it reads a teammate's change and approves it or asks for fixes.
- "I'm stopping this task for a while." → it writes a handoff note so someone else can continue.

---

## What only humans do

| You | When |
|---|---|
| **Approve your AI's proposals** | it will ask before claiming a task, merging, or anything risky |
| **Review a teammate's PR** when asked | ask your AI "review PR #N"; if Vercel posts a preview link on the PR, click through the change there |
| **Check the live site after your merge** | open https://drishti-lyart.vercel.app and look at what changed |
| **Research tasks marked "human task"** | e.g. T001: download the 2023 guidelines from an Indian connection |
| **Keep private data private** | the pack, passwords and demo logins stay on your machine; this repo is public |

## What only the owner does (label `needs-owner`)

Hosted database and Vercel settings, API keys and anything that costs money, loading new data into the live
site (T106-style tasks), updating the data pack, adding collaborators, final calls on design decisions.
To ask the owner something, your AI adds the `needs-owner` label and mentions @AdityaMore776 on the issue.

---

## Words you'll hear

| Word | Meaning |
|---|---|
| repo | the project folder, stored on GitHub |
| commit | a saved snapshot of changes, with a message |
| push / pull | send your commits to GitHub / fetch everyone else's |
| branch | your separate copy for one task (`simran/T103-document-agent`) |
| PR (pull request) | "please merge my branch into main"; where review happens |
| draft PR | a PR that says "work in progress, not ready yet" |
| CI | the automatic checks on every PR (green tick = passed) |
| merge | the branch's changes join main (and go live) |
| merge conflict | two people changed the same lines; the AI combines them by hand |
| issue | a task ticket on GitHub; **assigned** = someone's on it |
| label | a tag on an issue: `ready`, `in-progress`, `blocked`, `needs-owner` |
| milestone | a group of tasks (M1 … M6) |
| `gh` | the GitHub command-line tool your AI uses |

## Where things are

| | |
|---|---|
| The manual all AIs follow | [`AGENTS.md`](../../AGENTS.md) |
| The task plan | [`TASKS.md`](TASKS.md) |
| The progress log | [`log/`](log/) |
| Private data pack | [`DATA-PACK.md`](DATA-PACK.md) |
| Where the build stands | [`docs/STATUS.md`](../STATUS.md) |
| What DRISHTI is, in plain words | [`docs/HOW-IT-WORKS.md`](../HOW-IT-WORKS.md) |
| Task tickets | https://github.com/AdityaMore776/drishti/issues |
| Pull requests | https://github.com/AdityaMore776/drishti/pulls |
