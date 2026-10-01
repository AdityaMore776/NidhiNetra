"""Paperwork engine: do the work's own papers agree with the portal? (T110: Document + Contractor)

Merged from the 12-checker plan's B4 Document and C3 Contractor Network (T051, 12 -> 8): both
read the same Utilisation Certificates. The facts come from the engine's own reader
(reader.py) over local OCR text, so any work's papers, old or new, meet the same checks.
Measured on the real pilot evidence (data/trial/paperwork_trial.py, FINDINGS B4/C3).

Which certificates are the work's own: the portal amount is what was PAID, so a certificate
belongs when its sanction covers the payment (within 10%), when a payment equals it, or when
its location is named in the description (the trial's rule; 284 of 286 files belong).

  P1 SANCTION_LATE           the certificate's sanction date is past the 75-day clock (para
                             3.12, election pauses left out); 0.30 rising to 0.60 at 4x
  P2 SANCTIONED_BEFORE_RECOMMENDATION  sanction dated 7+ days before the recommendation: one
                             of the dates is wrong (0.50; OCR can misread, so never "hard")
  P3 PAID_MORE_ON_PAPER       the certificates show more paid than the portal amount, by
                             more than 10% and Rs 10,000 (0.30)
  P4 OTHER_WORKS_PAPERS      papers attached, none of them this work's (0.30)
  facts     the vendor's share of the district's certified works, by its unique code (never a
            name), is kept as evidence, never a finding
  removed (T053) notes found on nearly every certificate, so they said nothing about the
            work: "in progress" on paper (282/285), blank certification boxes (427/429), an
            instalment-only certificate, a vendor-share note

  NOT_APPLICABLE  no papers attached on eSAKSHI (most works: the pilot covers 837)
  NOT_ASSESSABLE  papers attached, but the local reader can read none of them (Hindi,
                  handwritten, poor scans: 51% of other states' PDFs)
"""

from __future__ import annotations

import re
import time
from datetime import date

from drishti import reference
from drishti.agents.compliance.agent import graded, mcc_days
from drishti.agents.contract import AgentResult, Finding, Status

AGENT = "paperwork"
VERSION = "paperwork-1.1.0"
QUESTION = "Do the work's own papers agree with the portal?"
CONFIDENCE = 0.8              # typed portal forms, read by OCR: 6 compared field by field all right
EARLY_DAYS = 7
PAY_TOL, PAY_MIN = 0.10, 10_000.0


def _d(x) -> date | None:
    if x is None or isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _lakh(v: float) -> str:
    return f"Rs {v / 1e5:,.2f} lakh"


def names_its_place(cert: dict, work: dict) -> bool:
    words = re.findall(r"[a-z]{4,}", (cert.get("location") or "").lower())
    desc = (work.get("description") or "").lower()
    return bool(words) and any(w in desc for w in words)


def own_certificates(certs: list[dict], work: dict) -> list[dict]:
    """This work's certificates. A file can bundle certificates of several works with nearly
    the same amount (read by eye: Malakpur and Sherpur, Rs 1.07 lakh each); when the
    certificates name different places, those naming this work's place win."""
    own = [c for c in certs if belongs(c, work)]
    places = {(c.get("location") or "").strip().lower() for c in own if c.get("location")}
    if len(places) > 1:
        named = [c for c in own if names_its_place(c, work)]
        if named:
            return named
    return own


def belongs(cert: dict, work: dict) -> bool:
    amount = float(work.get("amount") or 0)
    sanctioned = cert.get("sanctioned_amount")
    if amount > 0 and sanctioned and 0.99 <= sanctioned / amount <= 1.10:
        return True
    if amount > 0 and any(a is not None and abs(a - amount) <= 1
                          for _d0, a in cert.get("payments") or []):
        return True
    words = re.findall(r"[a-z]{4,}", (cert.get("location") or "").lower())
    desc = (work.get("description") or "").lower()
    return bool(words) and any(w in desc for w in words)


def _quiet(status: Status, text: str, t0: float, **evidence) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))


def assess(work: dict, vendors=None) -> AgentResult:
    t0 = time.perf_counter()
    # papers only: photos are the Photo Evidence engine's (T310)
    files = [f for f in ((work.get("evidence") or {}).get("files")) or [] if f.get("ext") == "pdf"]
    # a certificate page whose fields could not be read is no certificate to compare
    certs_all = [c for f in files for c in f.get("certificates") or []
                 if c.get("sanctioned_amount") or c.get("location") or c.get("payments")]
    if not files:
        return _quiet(Status.NOT_APPLICABLE, "No papers are attached to this work on eSAKSHI, so "
                      "there is nothing to read. This is not a clean chit.", t0)
    readable = [f for f in files if f.get("readable")]
    certs = certs_all
    if not readable:
        return _quiet(Status.NOT_ASSESSABLE,
                      f"{len(files)} paper(s) attached, but the local reader cannot read them "
                      "(Hindi, handwritten or a poor scan). This is not a clean chit.", t0,
                      files=len(files))
    if not certs:
        return AgentResult(
            agent=AGENT, status=Status.ASSESSED, verdict="NO_CERTIFICATE_READ", risk=0.0,
            confidence=0.4, hard=False, version=VERSION,
            headline=(f"{len(files)} paper(s) attached and readable, but none is a portal "
                      "utilisation certificate, so nothing could be compared with the portal."),
            limitations=["Only eSAKSHI's typed utilisation certificate is read field by field "
                         "so far; bills and other papers are counted, not checked."],
            evidence={"files": len(files), "readable_files": len(readable)},
            duration_ms=int((time.perf_counter() - t0) * 1000))

    own = own_certificates(certs, work)
    findings: list[Finding] = []
    rec = _d(work.get("recommended_date"))
    amount = float(work.get("amount") or 0)
    limit = int(reference.clause("SANCTION_PERIOD")["establishes"]["sanction_period_days"])

    if not own:
        findings.append(Finding(
            "OTHER_WORKS_PAPERS",
            f"{len(certs)} certificate(s) are attached, but none matches this work's amount "
            f"({_lakh(amount)}) or place. Check that the right papers were uploaded.",
            hard=False, risk=0.30, evidence={"certificates": len(certs)}))
    sanctioned = sorted({d for c in own if (d := _d(c.get("sanction_date")))})
    if rec and sanctioned:
        s = sanctioned[0]
        days = (s - rec).days
        if days < -EARLY_DAYS:
            findings.append(Finding(
                "SANCTIONED_BEFORE_RECOMMENDATION",
                f"The certificate dates the sanction {s.isoformat()}, {-days:,} days before the "
                f"portal's recommendation date ({rec.isoformat()}); one of the two dates is "
                "wrong. Check the sanction order.",
                hard=False, risk=0.50, evidence={"sanction_date": str(s), "days": days}))
        elif days >= 0:
            waited = days - mcc_days(rec, s)
            if waited > limit:
                findings.append(Finding(
                    "SANCTION_LATE",
                    f"Sanctioned {waited:,} days after recommendation (certificate dated "
                    f"{s.isoformat()}; election pauses left out), {waited - limit:,} days past "
                    f"the {limit}-day limit (para 3.12).",
                    hard=False, risk=graded(waited, limit, 4 * limit, 0.30, 0.60),
                    evidence={"sanction_date": str(s), "days": waited, "limit": limit}))
    # one certificate is issued per payment (an instalment), and a file can carry the same
    # certificate twice: count each (date, amount) once (read by eye, 1 Oct 2026: 12 of 12
    # "differences" were part payments or a repeated page)
    paid = {(str(d0), a) for c in own for d0, a in c.get("payments") or [] if a}
    places = {(c.get("location") or "").strip().lower() for c in own if c.get("location")}
    notes: list[str] = []
    if len(places) > 1 and not any(names_its_place(c, work) for c in own):
        # several works' certificates in one file, and the description names none of their
        # places: which payments are this work's cannot be told (read by eye: Malakpur and
        # Sherpur, Rs 1.07 lakh each, in one file)
        notes.append(f"The attached file carries certificates for {len(places)} places and the "
                     "description names none of them, so this work's own payments were not "
                     "added up.")
        paid = set()
    if own and paid and amount > 0:
        total = sum(a for _d0, a in paid)
        if total > amount + max(PAY_MIN, PAY_TOL * amount):
            findings.append(Finding(
                "PAID_MORE_ON_PAPER",
                f"The certificates show {_lakh(total)} paid; the portal records "
                f"{_lakh(amount)}. Check which figure is right.",
                hard=False, risk=0.30, evidence={"paid_on_papers": total, "portal": amount}))
    # T053: notes that sit on nearly every certificate say nothing about this work and were
    # removed: "in progress" on paper while complete on the portal (282 of 285), blank
    # certification boxes (427 of 429), a certificate for one instalment only (most works).

    codes = sorted({c["vendor_code"] for c in own if c.get("vendor_code")})
    vendor_facts = []
    if vendors is not None:
        for code in codes:
            share, n = vendors.share(work.get("district_lgd"), code)
            vendor_facts.append({"vendor_code": code, "district_share": share,
                                 "district_works": n})
    # the vendor's share of the district is a fact (evidence), never a finding of its own

    findings.sort(key=lambda f: -f.risk)
    top = findings[0] if findings else None
    if top is None or top.risk == 0:
        headline = (f"{len(own)} certificate(s) of this work read; dates and amounts agree with "
                    "the portal as far as they can be read.")
    else:
        headline = top.text
    limitations = notes + ["Read from scanned papers by local OCR; a misread date or amount is "
                   "possible, so every finding says check."]
    if not any(_d(c.get("sanction_date")) for c in own):
        limitations.append("No sanction date could be read on this work's certificates (the "
                           "older form has none).")
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED,
        verdict=top.code if top and top.risk > 0 else "PAPERS_AGREE",
        risk=top.risk if top else 0.0, confidence=CONFIDENCE, hard=False, headline=headline,
        version=VERSION, findings=findings, limitations=limitations,
        evidence={"files": len(files), "certificates": len(certs), "own_certificates": len(own),
                  "vendor_codes": codes, "vendors": vendor_facts},
        duration_ms=int((time.perf_counter() - t0) * 1000))
