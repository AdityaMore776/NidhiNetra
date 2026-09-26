# Glossary

## MPLADS terms

| Term | Meaning |
|---|---|
| **MPLADS** | Members of Parliament Local Area Development Scheme. Each MP gets **₹5 crore a year** (non-lapsable) to recommend local development works. Run by MoSPI. |
| **MoSPI** | Ministry of Statistics & Programme Implementation — runs MPLADS and set problem statement SIH26102. |
| **eSAKSHI** | The web portal and app that has run MPLADS end to end since April 2023: recommendation, sanction, payments, uploads, public dashboard. |
| **Recommendation** | The MP proposes a work on eSAKSHI. |
| **Sanction** | The District Authority approves the work and names an Implementing Agency. Guideline: within 75 days (2016 text); a rejection is told to the MP within 45 days. |
| **District Authority (DA)** | Usually the District Collector's office; sanctions, monitors, pays and inspects works. Must inspect at least 10% of works a year (para 6.4). |
| **Implementing Agency (IA)** | The department or body that builds the work (PWD, rural works, a state corporation…). |
| **State Nodal Authority** | The state department that oversees MPLADS across districts. |
| **Utilisation Certificate (UC)** | A certificate that the money released was spent on the work (Annexure-VI). |
| **Completion certificate** | Certificate that the work is finished and handed over. |
| **Plaque** | The mandatory MPLADS signboard at every work. CAG found 4,918 works without one. |
| **Outside-constituency ceiling** | Up to ₹25 lakh a year for works outside the MP's own area (para 2.9). |
| **Prohibited works** | Works MPLADS may not fund — e.g. religious buildings, commercial establishments, private property (Annexure-II). |
| **Lok Sabha term** | The 17th Lok Sabha ended June 2024; the 18th is current. Works can straddle terms. |
| **CAG** | Comptroller and Auditor General of India. Its MPLADS performance audit (Report 31 of 2010-11) is our list of real, recurring problems. |
| **LGD** | Local Government Directory — the government's official codes and boundaries for states and districts. |
| **Census-2011 code** | An older district numbering. eSAKSHI's export uses it (in a field misleadingly named `district_lgd`). |
| **DIGIPIN** | India Post's digital address grid; used to compare locations of works. |
| **PMAY-G, GeoMGNREGA, Amrit Sarovar** | Government schemes that already verify works with geotagged photos or satellite imagery — the precedents for our methods. |

## DRISHTI terms

| Term | Meaning |
|---|---|
| **Agent** | A specialist check that answers one question about a work (e.g. "is the cost unusual?"). |
| **Finding** | Something an agent noticed, with evidence. Never an accusation. |
| **Hard / soft finding** | Hard = arithmetic against a rule or an exact match (e.g. over a ceiling, byte-identical photo). Soft = a statistical signal (e.g. unusual cost); capped so it can't make a work HIGH alone. |
| **Confidence** | How sure an agent is of its own reading (0–1). |
| **Risk score** | 0–100, the fused result of all agents. Bands: Low / Medium / High. |
| **Review queue** | Works in the Medium or High band, ordered by score × money at stake. |
| **Limited evidence** | Two or more agents could not assess the work — a low score here is not a clean chit. |
| **NOT_ASSESSABLE / NOT_APPLICABLE / NOT_BUILT** | "Couldn't check with this data" / "question doesn't arise yet" / "agent still in development". None of them counts as low risk. |
| **Peer band / cohort** | The spread of costs of similar works (same type, same district — or state/country if too few). |
| **Bulk order / bundle** | One recommendation covering many units (e.g. 217 street lights) — explains a high amount. |
| **Split work** | One work cut into pieces, each just under a limit. |
| **GPS stamp / overlay** | Location, date and time printed onto a photo by a GPS-camera app. |
| **Perceptual fingerprint (pHash)** | A compact code for what an image looks like, robust to resizing and brightness changes; used to find reused photos. |
| **ORB feature matching** | Matches distinctive points between two images; survives crops, rotation and screenshots. |
| **OCR** | Reading text from an image or scanned PDF. |
| **Baseline / rival method** | The simple or commonly used method (keyword search, Isolation Forest, 64-bit hash) each agent must beat on the same data. |
| **Kill criterion** | The result below which an agent stays switched off. |
| **REAL / SCENARIO / LIVE** | Where a record came from: the eSAKSHI data, a planted demo case, or a submission on our site. |
| **Research build** | The team's earlier offline codebase (`~/saakshya`) from which methods are ported. |
