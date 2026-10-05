# DRISHTI — the AI-eye on every MPLADS rupee

**Smart India Hackathon 2026 · Problem Statement SIH26102 · Ministry of Statistics & Programme Implementation (MoSPI)**
**Team NeuralNexus (Team ID 121911)**

> *Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation.*

DRISHTI is a risk-intelligence layer that sits on top of **eSAKSHI**, the government portal that runs the
MPLAD Scheme. It checks every MPLADS work, flags the ones an officer should look at, and explains
**why** in plain language, with the evidence and the guideline clause behind each flag.

**Live prototype:** https://drishti-lyart.vercel.app (login required; demo accounts are shared with judges on request)

---

> **Four agents (4 Oct 2026):** Cost, Duplicate Work, Time & Rules and Site Progress, each asking only about what is likely a real problem. Plan in plain words: [`docs/plans/T120-four-agents.md`](docs/plans/T120-four-agents.md).
>
> **Plan update (27 Sept 2026):** the build now follows the team's **NidhiNetra** blueprint — four engines (guideline compliance, cost, duplicate & split, delay) → one explained 0–100 risk score → alerts, role dashboards and a daily **Inspection Planner** → learning from field verdicts. Summary: [`docs/specs/2026-09-27-nidhinetra-blueprint.md`](docs/specs/2026-09-27-nidhinetra-blueprint.md).

## In one minute

- Every Member of Parliament gets **₹5 crore a year** to recommend local works: roads, lights, handpumps, halls.
  About **2.1 lakh works** are on eSAKSHI today.
- The District Authority has to sanction, monitor and inspect all of them. It cannot look at every one.
- Auditors (CAG) have found the same problems again and again: inflated costs, the same work funded twice,
  works split to dodge limits, works that don't follow the rules, missing plaques, delays, doubtful bills.
- **DRISHTI runs specialist AI agents over every work.** Each agent checks one kind of problem. Their
  results are combined into one **0–100 risk score** with the top reasons, and the riskiest works go into a
  **review queue** for the district officer.
- **Reads the real evidence:** eSAKSHI's public dashboard also serves the real **certificates, bills and
  geo-stamped site photos** behind each work. DRISHTI reads that evidence, not just the spreadsheet, and
  every agent is tested on real government data before it goes live.
- **DRISHTI never accuses anyone.** It says "needs verification", never "fraud". An officer always decides.

## What works today

| | State |
|---|---|
| **Live web app** | Dashboard with India map, review queue, works search, work detail page with the agent cards and the score breakdown. Three roles (Ministry, District, Field), each seeing only what it should. |
| **Real data** | All **2,09,993** real eSAKSHI works loaded and assessed. **1,524 works (0.73%)** in the review queue (High + Critical): works where two checks agree. 24 of 30 random queue works, read by eye, are worth checking. |
| **Built engines** | The four agents (4 Oct 2026): **Cost** (every line of the agency's cost estimate form at a fair rate for the district, then the whole estimate; no form, no price judgment), **Duplicate Work** (the form's map pin against sanctioned works of the same kind, declared continuations, and one job cut into pieces just under a limit), **Time & Rules** (the 75-day sanction clock as an office fact, impossible dates, and a comfort window from the agency's own estimated time), **Site Progress** (monthly site videos filmed in the app, sealed, checked for reused footage, the wrong place and claims not shown), and the **0–100 risk score** with its top three reasons in English and Hindi. |
| **Real-evidence trial** | Every planned agent was tried on **real evidence for 837 completed works** (905 files downloaded from eSAKSHI's public endpoints, 1,925 pages read). Results: [`docs/trial/FINDINGS.md`](docs/trial/FINDINGS.md). |

### Headline results from the real-data trial

| Agent | Result on real data |
|---|---|
| **Cost** | catches **63%** of works inflated 5× (84% at 10×), with 1.5% false alarms |
| **Eligibility** | **56%** of flags plainly prohibited, 80% worth an officer's look (fresh sample) |
| **Photo Forensics** | recognises **99.9%** of edited copies (crop, stamp, screenshot, rotate) |
| **Split works** | 12× more works just under ₹5 lakh than just over; 136 bulk-order groups (744 works) kept under the limit |
| **Geo-Location** | GPS stamps read on 170 works; found 3 works whose own photos show them finished *before* the MP recommended them |
| **Document** | reads sanction date, payments and contractor off 431 UP certificates **for free** (local text reading); 16% sanctioned after the 75-day limit |

Weak or untested results are reported just as plainly (delay prediction is only slightly better than an
office's past record; satellite is a no-go for now). See [`docs/AGENT-CATALOG.md`](docs/AGENT-CATALOG.md).

---

## Read more

| If you want… | Read |
|---|---|
| **How DRISHTI works, in plain words** (no code) | [`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md) |
| **Every agent**: what it checks, how, how it was tested, where it stands | [`docs/AGENT-CATALOG.md`](docs/AGENT-CATALOG.md) |
| **Real-data trial**, agent by agent, with every number | [`docs/trial/FINDINGS.md`](docs/trial/FINDINGS.md) |
| **Technical architecture**: components, scoring maths, API, database, security | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| **Data**: sources, the evidence harvester, privacy, known traps | [`docs/DATA.md`](docs/DATA.md) |
| **Run it yourself**: local setup, tests, deployment | [`docs/SETUP.md`](docs/SETUP.md) |
| **Where the build is and what's next** | [`docs/STATUS.md`](docs/STATUS.md) |
| **MPLADS and project terms** | [`docs/GLOSSARY.md`](docs/GLOSSARY.md) |
| **Joining the team?** How we work together (humans + their AI agents) | [`docs/team/README.md`](docs/team/README.md) · AI manual: [`AGENTS.md`](AGENTS.md) |
| **The task plan** and who's doing what | [`docs/team/TASKS.md`](docs/team/TASKS.md) · [Issues](https://github.com/AdityaMore776/NidhiNetra/issues) · [progress log](docs/team/log/) |
| **Team rules** for working on the repo | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Design documents | [`docs/specs/`](docs/specs/) (v2 = current design) |
| The SIH idea-submission deck | [`docs/deck/DRISHTI_SIH26102_v2.pdf`](docs/deck/DRISHTI_SIH26102_v2.pdf) |

## Repository map

```
drishti/
├── apps/
│   ├── engine/          Python FastAPI service: agents, validation, fusion, API  (259 tests)
│   │   └── drishti/
│   │       ├── agents/          agent contract + the Cost ("statistical") agent
│   │       ├── validation/      data checks: impossible dates, prohibited-work notes
│   │       ├── fusion/          combines agent results into the 0–100 score
│   │       ├── pipeline/        runs validation → agents → fusion for one work
│   │       ├── api/             REST endpoints used by the web app
│   │       ├── reference/       guideline clauses, prohibited works, work types (YAML)
│   │       └── migrations/      database schema (SQL)
│   └── web/             Next.js dashboard: map, queue, works, work detail, login
├── data/                offline jobs: build the corpus and statistics, load the database,
│   ├── harvest/         download eSAKSHI evidence politely (pilot sample)
│   └── trial/           the real-data trial of every agent, and its results (JSON)
├── docs/                everything a reader needs (see the table above)
│   └── team/            the team system: task plan, progress log, data pack, how we work
├── scripts/team/        sync (session briefing), new_log, check_pr, data-pack tools
├── scripts/dev/         local_db.py: local Postgres with the real corpus
├── AGENTS.md            the operating manual every AI agent on the team follows
├── .github/             CI (tests, team checks, secret scan), issue and PR templates
└── vercel.json          hosting: web and engine as two services on one domain
```

## Tech stack

**Web:** Next.js 16 (React 19), Tailwind CSS 4, MapLibre maps on official LGD boundaries ·
**Engine:** Python 3.12, FastAPI, psycopg 3 · **Database & login:** Supabase (PostgreSQL, Auth) ·
**Analysis:** pandas, scikit-learn, perceptual hashing + ORB (OpenCV), local OCR (RapidOCR, PyMuPDF), LightGBM (trial) ·
**Hosting:** Vercel (Mumbai database region) · **Planned:** Gemini vision for Hindi/handwritten papers
and site photos, Sentinel-2 for large works only.

## Principles we don't break

1. **Needs verification, never "fraud".** Accusing words are blocked in code (`BANNED_WORDS`); a test fails if any agent uses one.
2. **"Could not check" is not a clean chit.** An agent that cannot assess a work says so; it never counts as low risk.
3. **Proof before launch.** An agent goes live only after it meets its accuracy target on real data. If it fails, it stays off.
4. **Only measured numbers.** Every figure in this repo comes from a script whose output is saved in `data/trial/results/`.
5. **Privacy.** Downloaded evidence, OCR text, phone numbers and bank account numbers never enter git or the screen.

---

*Data: MPLADS eSAKSHI public dashboard (snapshot 26 May 2026), LGD boundaries, CAG Report 31 of 2010-11. This is a
hackathon prototype, not an official government system; findings are leads for an officer to check, not rulings.*
