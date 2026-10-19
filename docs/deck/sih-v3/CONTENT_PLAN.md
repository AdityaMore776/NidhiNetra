# DRISHTI — SIH 2026 idea deck v3: content plan + fact ledger

Template: `~/Downloads/NMIET_SIH_2026_PPT_Template.pptx` (1280×720 px canvas, 7 slides).
Workspace: this folder (ppt-master Edit Native PPTX round-trip). Output: 6 slides → PDF for the portal.

## Template rules (slide 7 of the template — dropped from output)
- Max 6 slides incl. title · points / diagrams / infographics, no paragraphs · PDF upload only.
- "Use the provided template without changing the idea details pointers" → every pointer heading is kept
  word-for-word (restyled smaller, never reworded).
- Chrome kept: SIH 2026 logo, team-name oval (→ NeuralNexus), black serif title, blue footer
  "@SIH Idea submission- Template" + page number.

## Output roster
| Out | Source slide | Mode | Content |
|---|---|---|---|
| 1 | 1 | edited | Title page: DRISHTI + tagline; six template fields filled |
| 2 | 2 | edited | Idea title + Proposed Solution; three pointers; life-of-a-work agent band |
| 3 | 3 | edited | Technical Approach: methodology flow diagram + live prototype screenshot + tech stack |
| 4 | 4 | edited | Feasibility: real-data scorecard + cost-agent chart; challenges → strategies |
| 5 | 5 | edited | Impact: stakeholders, findings already surfaced, benefits, roadmap |
| 6 | 6 | edited | References (verified) + GitHub/live links + the ONE comparison chart |
| — | 7 | dropped | template instructions |

## Framing rules (user)
- No "better than rivals" anywhere except the comparison chart on slide 6.
- Our measured accuracy on real eSAKSHI works speaks for itself.
- "Needs checking", never "fraud". Honest gaps shown (Satellite off, Citizen demo-only, Delay weak).

## Fact ledger (every number on a slide → its source)
| Fact | Source |
|---|---|
| ₹5.00 crore per MP per year since 2011-12 | PIB release 2155040, 11 Aug 2025 (fetched 26 Sep 2026) |
| eSAKSHI launched 1 April 2023; single ₹5 cr instalment | PIB release 2155040 |
| Funds non-lapsable | MPLADS Guidelines (June 2016) para 4.4 |
| Sanction within 75 days; rejection told within 45 days | Guidelines 2016 para 3.12 |
| Completion generally within one year | Guidelines 2016 para 3.13 |
| Plaque at every work | Guidelines 2016 para 3.22 |
| District Authority inspects ≥10% of works every year | Guidelines 2016 para 6.4(i) |
| 4,918 works without plaque, 31 DAs (₹100.20 cr) | CAG Report No. 31 of 2010-11, Annex 7.2 TOTAL row (local text + live URL, same 8,269,196-byte file) |
| 12,006 incomplete works, ₹279.99 cr, 71 DAs | CAG Report No. 31 of 2010-11, Annex 4.7 TOTAL row |
| ~~7,230 works sanctioned without following guidelines~~ | NOT found in the report text → not used |
| 2,09,993 real works (snapshot 26 May 2026) | docs/DATA.md |
| 66% of completed works carry files | docs/DATA.md |
| Live: all works assessed; queue 276 (0.13%) | docs/STATUS.md "At a glance" |
| Cost: 18% / 39% / 63% / 84% at 2× / 3× / 5× / 10×; 1.5% false alarms | trial/FINDINGS.md A3 |
| Photo: 99.9% of edited copies recognised; 319 photos, 50,678 pairs | FINDINGS B2 |
| Geo: stamps on 190 photos/pages, 170 works; coords right 12/12; 3 works finished before recommended | FINDINGS B3 |
| GPS metadata stripped: 0 of 321 photos | FINDINGS B3 |
| Document: 431 UP certificates; amounts/payment dates ≥99%; 16% sanctioned after 75 days; 282 of 285 "completed" works' certificate says "in progress" | FINDINGS B4 |
| 51% of other states' PDFs need AI reading | FINDINGS B4 (158 of 308) |
| Eligibility v2: 56% plainly prohibited, 80% worth a look (fresh sample of 50) | FINDINGS A1 |
| 12.1× more works just under ₹5 lakh than just over | FINDINGS A2 |
| 136 bulk-order groups (744 works) | FINDINGS A2 |
| Delay model 0.71 vs office record 0.68 | FINDINGS C1 |
| 40,489 works (₹2,178 cr) of 97,808 recommended Apr 2023–May 2024 not complete 2 years on | FINDINGS C1 |
| 21,323 works (₹1,361 cr) waiting for sanction past 75 days; median 239 days | FINDINGS C2 |
| Pratapgarh: top 3 of 7 vendors hold 84% of 261 works | FINDINGS C3 |
| 21,789 of 21,793 citizen ratings are zero | FINDINGS D1 |
| Tech stack (Next.js 16, React 19, Tailwind 4, MapLibre 6, Python 3.12, FastAPI, Supabase Postgres Mumbai, Vercel) | docs/ARCHITECTURE.md |
| LightGBM, scikit-learn, OpenCV ORB + RANSAC, 256-bit pHash, RapidOCR + PyMuPDF | data/trial/*.py imports |

## References (all checked)
- MPLADS Guidelines, June 2016 (MoSPI) — https://cdnbbsr.s3waas.gov.in/s3c3614206a443012045cfd75d2600af2d/uploads/2023/02/2023020891.pdf
- PIB release 2155040 (11 Aug 2025), Revised MPLADS Guidelines 2023 — https://www.pib.gov.in/PressReleasePage.aspx?PRID=2155040
- CAG Report No. 31 of 2010-11, Performance Audit of MPLADS — https://cag.gov.in/uploads/download_audit_report/2010/Union_Performance_Local_area_Development_Scheme_31_2010_annexures.pdf
- eSAKSHI public dashboard — https://mplads.mospi.gov.in
- Rublee, Rabaud, Konolige, Bradski — ORB: an efficient alternative to SIFT or SURF, ICCV 2011
- Fischler & Bolles — Random Sample Consensus, Communications of the ACM 24(6), 1981
- Zauner — Implementation and Benchmarking of Perceptual Image Hash Functions, MSc thesis, Hagenberg, 2010
- Ke et al. — LightGBM, NeurIPS 2017
- Wilson — Probable inference, the law of succession, and statistical inference, JASA 22(158), 1927
- Data: LGD district outlines (via github.com/yashveeeeeeer/india-geodata); India Post PIN–district mapping
- Project: https://github.com/AdityaMore776/drishti · live https://drishti-lyart.vercel.app

## Unverified — kept OFF the slides
- 2023 Guidelines text (mplads.gov.in refuses outside connections) → all clause numbers cite the 2016 edition.
- "₹4,000 cr annual outlay" (v2 deck) → not stated in a source we hold.
- "7,230 works sanctioned without following guidelines" → not in the CAG report text.
