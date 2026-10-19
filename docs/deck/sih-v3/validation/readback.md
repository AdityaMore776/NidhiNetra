<!-- Slide number: 1 -->
# SMART INDIA HACKATHON 2026

![Picture 1](Picture1.jpg)
DRISHTI

![Image 12](Image12.jpg)
The AI-eye on every MPLADS rupee
AI checks on every MPLADS work — flags what needs checking, with the evidence

![Picture 4](Picture4.jpg)
Problem Statement ID –
SIH26102

Problem Statement Title-
Development of an AI-powered system to detectanomalies, fraud, and inefficiencies in MPLAD Schemeimplementation regd.

Organisation-
Ministry of Statistics & Programme Implementation(MoSPI)

Theme-
Smart Automation

PS Category-
Software

Team ID-
121911

Team Name-
NeuralNexus

### Notes:
Good morning. We are team NeuralNexus, and our problem statement is SIH26102 from the Ministry of Statistics and Programme Implementation: finding anomalies, fraud and inefficiencies in how MPLADS works are carried out. Our answer is DRISHTI, which means sight. It looks at every MPLADS work and tells an officer which ones need checking first, and why.

<!-- Slide number: 2 -->

DRISHTI  ·  the AI-eye on every MPLADS rupee

![Picture 10](Picture10.jpg)
NeuralNexus
Proposed Solution (Describe your Idea/Solution/Prototype)

DRISHTI is a read-only AI layer on top of eSAKSHI. 12 specialist agents check every MPLADS work at every stage, read the certificates, bills and geo-tagged photos already uploaded to eSAKSHI, andturn what they find into a short, ranked inspection list for District Authorities — every flag with its evidence and the guideline clause.
12 AGENTS ACROSS THE LIFE OF A WORK
THEN, FOR EVERY WORK

Risk Fusion
BEFORE SANCTION
DURING CONSTRUCTION
MONEY & TIME
AFTER COMPLETION
1
2
3
4

one 0–100 score, parts add up
Eligibility forbidden works
Site Progress claim vs photo, plaque
Delay stuck works, late offices
Citizen Verification asset exists, in use

Duplicate & Split repeats, split-ups
Photo Forensics reused photos
Fund Flow money left waiting

Review queue

ranked by risk × money
Cost inflated estimates
Geo-Location where & when shot
Contractor a few firms win all

Document papers that don't add up

Inspection plan
Satellite big works only

the 10% of visits (para 6.4)
Live in the prototype
Tested on real eSAKSHI works, being moved into the live engine
Planned / not yet testable on public data

Detailed explanation of the proposed solution

Each agent answers one plain question — e.g. “Was this photo alreadyused on another work?”

Reads what eSAKSHI already holds: 2,09,993 works plus the completionand utilisation certificates, bills and site photos uploaded for them.

Risk Fusion adds the agents into one 0–100 score. The parts add upexactly, so an officer sees why.

Next: officers' verdicts from each visit become labels that retrain theagents.

How it addresses the problem

4,918 works had no MPLADS plaque CAG audit, 31 districts
? Plaque and photo checks at every work
?279.99 cr stuck in 12,006 incomplete works CAG audit, 71 districts
? Stuck-work list + each office's track record
Sanction is due within 75 days Guidelines ¶3.12
? Flags works left waiting past the limit
District must inspect ?10% of works Guidelines ¶6.4
? Risk-ranked list of which works to visit
Innovation and uniqueness of the solution

Reads the GPS stamp printed into site photos. eSAKSHI strips the phone'sown GPS data (0 of 321 photos kept it).

Proof before launch: an agent goes live only after it meets its accuracytarget on real eSAKSHI works.

Never accuses. It says “needs checking”, cites the guideline clause, andshows “could not assess” honestly.

Reads typed certificates with free, on-server text reading; paid AI only forHindi and handwritten papers.

@SIH Idea submission- Template
2

### Notes:
DRISHTI sits on top of eSAKSHI and only reads from it, so no officer has to enter anything new. Twelve agents follow a work from recommendation to completion, and each one answers a single question, such as whether this photo was already used on another work. Their findings are combined into one score out of 100, and the parts add up exactly, so an officer can see which agent raised a work and disagree with any single part. That ranked list becomes the ten percent of works the District Authority must inspect every year under para 6.4 of the guidelines. The problems we target come from the CAG audit and the guidelines themselves, for example 4,918 works that never got the mandatory plaque.

<!-- Slide number: 3 -->
# TECHNICAL APPROACH

![Picture 11](Picture11.jpg)
NeuralNexus
Technologies to be used (e.g. programming languages,frameworks, hardware)

Frontend
Next.js 16 · React 19 · Tailwind CSS 4MapLibre maps
Backend & API
Python 3.12 · FastAPI · role-based sign-in(Supabase Auth)

Database
PostgreSQL on Supabase, Mumbai region
ML & statistics
LightGBM · scikit-learn · pandas · NumPy

Photos & papers
OpenCV feature matching · 256-bit photofingerprints · RapidOCR + PyMuPDF text reading
AI reading
Gemini vision for Hindi / handwritten papers andsite progress (planned, capped)

Maps & places
Official LGD district outlines · India Post PIN codesDIGIPIN grid (planned)
Hosting & CI
Vercel · GitHub Actions runs every test on eachpush

Security & privacy
Secrets only in server settings · district scopinginside every database query · phone and banknumbers masked
Hardware
None to buy — officers use a browser or a phone
Methodology and process for implementation (Flow Charts/Images/ working prototype)

eSAKSHI data
Data Validation
12 agents
Risk Fusion
Review queue
2,09,993 workscertificates, bills,site photos
dates & amountsreads papers, stampsmasks phone & bank nos.
0–100 scoretop reasonsparts add up
Ministry · District ·Field dashboardsevidence + clause

3 Before sanction
5 Construction

3 Money & time
1 After completion

verdicts become labels that retrain agents
Officer verdict
the human decides

![Image 81](Image81.jpg)
WORKING PROTOTYPE — LIVE
drishti-lyart.vercel.app · sign-in by role
All 2,09,993 real works assessed; 276 (0.13%) sit in the review queue.

Live today: Cost agent, Data Validation, Risk Fusion, India map on official LGD outlines.

Tried offline on 837 real completed works and their 905 downloaded files.

Code and full trial write-up: github.com/AdityaMore776/drishti

EVERY AGENT ANSWERS IN THE SAME FORM
status checked · not applicable · could not assess
risk + confidence 0–1 each
headline one plain sentence for the officer
evidence the photo, paper or number behind it
limits what it could not check — always shown

@SIH Idea submission- Template
3

### Notes:
On the left is the stack we actually run: Next.js for the screens, a Python FastAPI engine, and PostgreSQL on Supabase in the Mumbai region, hosted on Vercel. The flow on the right is how one work moves through the system: eSAKSHI data is checked and cleaned, the agents run, Risk Fusion ranks the result, and an officer makes the final call. The screenshot is the live prototype, which has assessed all 2,09,993 real works and puts 276 of them in the review queue. Every agent answers in the same form, including what it could not check, so a missing check is never shown as a clean result.

<!-- Slide number: 4 -->
# FEASIBILITY AND VIABILITY

![Picture 10](Picture10.jpg)
NeuralNexus
Analysis of the feasibility of the idea

Agent
How we tested it on real eSAKSHI data
Result
Status

Cost
1,000 real works inflated; 20,000 untouched
Catches 63% of 5× mark-ups (84% of 10×); 1.5% false alarms
LIVE

Photo Forensics
319 real site photos, each edited 6 ways
Recognises 99.9% of edited copies
TESTED

Geo-Location
GPS stamps on 190 photos / pages, 170 works
Coordinates right on all 12 checked by eye
TESTED

Document
431 Uttar Pradesh utilisation certificates
Amounts and payment dates read on ?99%
TESTED

Eligibility
Fresh sample of 50 flagged works
56% plainly prohibited; 80% worth an officer's look
TESTED

Split works
All 2,09,993 works
12× more works just under ?5 lakh than just over
TESTED

Delay
Trained to Jan 2025; tested Jan–May 2025
Ranking score 0.71 vs 0.68 for office record alone
WEAK

Satellite
170 works with coordinates
Median work ?2.8 lakh — too small for 10 m pixels
OFF

Citizen
eSAKSHI citizen ratings
21,789 of 21,793 ratings are zero
DEMO

Potential challenges andrisks
Strategies for overcomingthese challenges

No confirmed fraud labels
Planted test cases on real works;officers' verdicts become labels.
Few proven cases to learn from.

False alarms
Price alone can never make a workhigh-risk; separate agents mustagree.
Bulk orders, terrain and rates can looklike overpricing.

Hindi & handwritten papers
Unclear reading = “can't tell”, neveran alert; AI reader behind a cappedswitch.
51% of other states' PDFs can't be readlocally.

Personal data
Masked before display; accessscoped by role and district.
Phone and bank account numbers sit inpublic records.

Portal habits look like misconduct
Each office compared with the sameperiod nationally.
e.g. bulk entry when eSAKSHI opened in2023.

Technical feasibility
Data feasibility
Live prototype on Vercel +Supabase; every agent followsone reporting contract.
2,09,993 works loaded. 2 in 3completed works carrycertificates or photos.

Operational feasibility
Economic feasibility
Read-only on eSAKSHI: no newdata entry; fits the MP ? District? Agency flow.
Open-source stack and free textreading; paid AI only behind acapped switch.
Cost agent: inflated works caught
84%

63%

39%

18%

2×
3×
5×
10×
Mark-up applied to 1,000 real works.
False alarms on 20,000 untouched works: 1.5%

PROOF BEFORE LAUNCH
An agent goes live only after it meets its accuracy target on real eSAKSHI works. If it fails,it stays switched off.

@SIH Idea submission- Template
4

### Notes:
Every result in this table comes from real eSAKSHI works, and we list the weak and switched-off agents alongside the ones that work. The cost agent, which is live, catches 63 percent of estimates inflated five times over while flagging 1.5 percent of normal works. Photo forensics recognised 99.9 percent of edited copies of real site photos, and the certificate reader picked out amounts and payment dates on at least 99 percent of 431 Uttar Pradesh certificates. Delay prediction was only slightly better than an office's past record, so we show it as a track record, and satellite stays off because the works we could place were too small to see. On the right are the main risks, such as false alarms and handwritten Hindi papers, with how we handle each one; the rule underneath is that an agent goes live only after it meets its accuracy target.

<!-- Slide number: 5 -->
# IMPACT AND BENEFITS

![Picture 10](Picture10.jpg)
NeuralNexus
Potential impact on the target audience

Ministry (MoSPI)
State Nodal Authorities
District Authorities
MPs & citizens
National risk map by state and district
District and agency track records
276 works to review instead of 2,09,993
Live status of recommended works

Sanction backlog and fund use, by Lok Sabhaterm
Stuck or high-risk works to escalate
The 10% inspection plan, ranked by risk ×money
Early warning on stuck works

Contractor concentration, from certificates
Citizens confirm completed assets (planned)

Each agent's accuracy tracked openly
Eligibility and cost checks before sanction

ALREADY FOUND IN REAL eSAKSHI DATA — each one needs checking, none is a verdict

21,323
40,489
136
282 / 285
3
works (?1,361 cr) waiting for sanctionpast the 75-day limit
works (?2,178 cr) recommended Apr2023–May 2024, still not complete twoyears on
groups of bulk orders (744 works) keptjust under ?5 lakh each
“completed” works whose certificatestill says “in progress”
works whose own photos show themfinished before the MP recommendedthem
Benefits of the solution (social, economic, environmental, etc.)

SOCIAL
ECONOMIC
ENVIRONMENTAL
Assets exist where they are claimed
Risk flagged before money moves
Remote checks from photos & GPS stamps

Forbidden works caught before sanction
Split works, repeats, padded costs caught
Fewer wasted site trips and fuel

Public trust through open records
Officer visits go where risk is highest
Paperless, searchable records

Next steps

Live prototype + trial on 837 real works
?

Document + Contractor agents
M1

Eligibility v2, splits and repeats
M2

Photo Forensics + Geo-Location
M3

AI reader, field app, Inspection Planner
M4–M6

Officers' time goes where the evidence is: 0.13% of works, each with its
2,09,993 works ? 276 to check first
reasons, the guideline clause, and what DRISHTI could not check.

@SIH Idea submission- Template
5

### Notes:
Each level of government gets a different view: the Ministry sees the national map and the sanction backlog, and a District Authority sees a short list of works to visit. The orange tiles are things DRISHTI has already found in public eSAKSHI data. For example, 21,323 works worth 1,361 crore rupees are still waiting for sanction past the 75 day limit, and three works have photos showing them finished before the MP recommended them. We present each of these as something to check, never as a verdict. Next we move the Document and Contractor agents into the live engine, followed by eligibility, split works, photo checks and the field app.

<!-- Slide number: 6 -->
# RESEARCH  AND REFERENCES

![Picture 11](Picture11.jpg)
NeuralNexus
Details / Links of the reference and research work

GOVERNMENT & SCHEME SOURCES
1
MoSPI — Guidelines on MPLADS (June 2016), paras 2.1, 3.12, 3.13, 3.22, 4.4, 6.4
cdnbbsr.s3waas.gov.in/s3c3614206a443012045cfd75d2600af2d/uploads/2023/02/2023020891.pdf
2
PIB — Revised MPLADS Guidelines 2023 (release 2155040, 11 Aug 2025)
pib.gov.in/PressReleasePage.aspx?PRID=2155040
3
CAG — Report No. 31 of 2010-11, Performance Audit of MPLADS (Annex 4.7, 7.2)
cag.gov.in/uploads/download_audit_report/2010/Union_Performance_Local_area_Development_Scheme_31_2010_annexures.pdf
4
MoSPI — eSAKSHI public dashboard and uploaded files (data to 26 May 2026)
mplads.mospi.gov.in
METHODS WE USE
5
Rublee, Rabaud, Konolige, Bradski — ORB: an efficient alternative to SIFT or SURF. ICCV 2011
6
Fischler & Bolles — Random Sample Consensus (RANSAC). Comm. ACM 24(6), 1981
7
Zauner — Implementation and Benchmarking of Perceptual Image Hash Functions. MSc thesis, 2010
8
Ke et al. — LightGBM: a highly efficient gradient boosting decision tree. NeurIPS 2017
9
Wilson — Probable inference, the law of succession, and statistical inference. JASA 22(158), 1927
DATA & TOOLS
•
LGD district outlines (via github.com/yashveeeeeeer/india-geodata) · India Post PIN–district mappingOpenCV · scikit-learn · RapidOCR · PyMuPDF
How DRISHTI compares with existing monitoring

Capability
Existing systems*
DRISHTI

PARTLY
YES
Coverage
Every work stored; audits check a sample
Every work assessed — 2,09,993 today

PARTLY
YES
Cost vs similar works
Manual review in audits
Live: district cost bands for every work

NO
YES
Reused or edited photos
Photos viewed by eye
99.9% of edited copies recognised

PARTLY
YES
Photo place & time
Geotag shown on a map
GPS stamp read; district and date checked

NO
YES
Reads certificates & bills
Stored as files
Sanction date, payments, vendor read

NO
PARTLY
Split works & repeats
Not automated
Splits found; reworded repeats next

NO
YES
Risk-ranked review list
Sample picked by hand
276 works ranked by risk × money

NO
YES
Explains each flag
—
Evidence + guideline clause, every flag

NO
PARTLY
Site progress from photos
Checked by eye
Planned: AI vision, behind a switch

*eSAKSHI, PMAY-G AwaasApp, GeoMGNREGA / NMMS, CAG and social audits — as described in their public documents.

OUR WORK — OPEN TO CHECK
Code github.com/AdityaMore776/drishti
Every number:
Live demo drishti-lyart.vercel.app
docs/trial/FINDINGS.md

@SIH Idea submission- Template
6

### Notes:
All our government sources are public, and each one has a link here: the MPLADS guidelines, the PIB release on the 2023 revision, the CAG performance audit and the eSAKSHI dashboard. The methods papers are the ones behind the code we run, such as ORB feature matching for photos and LightGBM for the delay model. The table on the right is the only comparison in this deck, and it compares DRISHTI with how existing systems check works, based on their own public documents. The code, the live demo and the write-up behind every number are open at the links at the bottom left.
