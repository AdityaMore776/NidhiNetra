"""Read eSAKSHI's Utilisation Certificates from OCR text (T051, ports T102).

Ported from data/trial/document_trial.py, where it was measured on 431 real certificates
(amounts, payment dates and status read on >= 99%, vendor 98%, sanction date 69%). Pure
functions over one OCR page: {"page": n, "lines": [[box, text, confidence], ...]}, box = four
[x, y] corners, as the local OCR (rapidocr) writes them. Any OCR that gives boxes and text
works; nothing here knows which works or districts the papers came from.

The portal generates the certificate (Annexure-VI), it is printed, signed and scanned back:
implementing agency, work name and location, sanction date, sanctioned amount, the vendor's
unique code, work status, each payment's approval date and amount. Two form versions exist; the
older one has no sanction-date line, so the certification paragraph ("Certified that out of
Rs. X ... sanctioned on DD/MM/YYYY") is the fallback.

Never kept: the vendor's NAME and bank account (the reader does not return them).
"""

from __future__ import annotations

import re
from datetime import date, datetime

# OCR noise (2 Oct 2026): RapidOCR drops spaces ("TESTVENDORV123456789012"), reads "/" as "|"
# and prints dates with "-" or "."; a zero can come back as the letter O ("3,OO,OOO").
VENDOR_CODE = re.compile(r"(?<!\d)V\d{12}(?!\d)")
DATE = r"(\d{2}[/|.\-]\d{2}[/|.\-]\d{4})"
AMOUNT = r"([\d,]+(?:\.\d+)?)"
_NUMBERISH = re.compile(r"(?<![A-Za-z])[0-9Oo][0-9Oo,./|\-]*(?![A-Za-z])")


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def zeros_in_numbers(text: str) -> str:
    """The letter O read for a zero, put back, inside numbers only ("2O/O3/2O24")."""
    def fix(m: re.Match) -> str:
        s = m.group(0)
        return s.replace("O", "0").replace("o", "0") if any(c.isdigit() for c in s) else s
    return _NUMBERISH.sub(fix, text)


def ordered_lines(page: dict) -> list[dict]:
    """Boxes in reading order. Boxes whose vertical centres sit within half a line height of
    the current row join it, so a label and its value on one printed line stay together."""
    boxes = [{"x": min(p[0] for p in box), "y": min(p[1] for p in box),
              "h": max(p[1] for p in box) - min(p[1] for p in box), "text": text}
             for box, text, *_ in page.get("lines") or []]
    for b in boxes:
        b["cy"] = b["y"] + b["h"] / 2
    if not boxes:
        return []
    half = sorted(b["h"] for b in boxes)[len(boxes) // 2] / 2
    rows, current = [], []
    for b in sorted(boxes, key=lambda b: b["cy"]):
        if current and b["cy"] - sum(c["cy"] for c in current) / len(current) > half:
            rows.append(current)
            current = []
        current.append(b)
    rows.append(current)
    return [b for row in rows for b in sorted(row, key=lambda b: b["x"])]


def after_colon(label: str, lines: list[dict]) -> str | None:
    key = squash(label)
    for r in lines:
        t = r["text"]
        if squash(t).startswith(key):
            v = t.split(":", 1)[1] if ":" in t else t[len(label):]
            v = v.strip(" :")
            return v or None
    return None


def _money(s: str | None) -> float | None:
    try:
        return float(s.replace(",", "")) if s else None
    except ValueError:
        return None


def to_date(s: str | None) -> date | None:
    try:
        return (datetime.strptime(re.sub(r"[|.\-]", "/", s), "%d/%m/%Y").date()
                if isinstance(s, str) else None)
    except (ValueError, TypeError):
        return None


def page_kind(page: dict) -> str:
    flat = squash(" ".join(t for _box, t, *_ in page.get("lines") or []))
    if "utilizationcertificate" in flat and "nameofwork" in flat:
        return "utilisation_certificate"
    if "havingbeenfullysatisfied" in flat or "grants-in-aidofmpladsscheme" in flat:
        return "utilisation_certificate_p2"
    if "completioncertificate" in flat:
        return "completion_certificate"
    if "measurementbook" in flat:
        return "measurement_book"
    if any(k in flat for k in ("taxinvoice", "invoiceno", "gstin", "billno")):
        return "bill_invoice"
    if "gpsmapcamera" in flat or re.search(r"lat[^a-z]{0,3}\d{1,2}\.\d{3,}", flat):
        return "gps_photo_page"
    if len(page.get("lines") or []) < 5:
        return "photo_or_blank"
    return "other_or_unreadable"


def parse_uc(page: dict) -> dict | None:
    """The typed fields of a certificate's first page, else None."""
    lines = ordered_lines(page)
    flat = squash(" ".join(zeros_in_numbers(r["text"]) for r in lines))
    if "utilizationcertificate" not in flat or "nameofwork" not in flat:
        return None
    f = {"agency": after_colon("Implementing Agency", lines),
         "work_name": after_colon("Name of Work", lines),
         "location": after_colon("Location of Work", lines)}
    m = re.search(r"sanctiondate.{0,40}?" + DATE, flat)
    f["sanction_date"] = to_date(m.group(1)) if m else None
    m = re.search(r"totalsanctionedamountforthework:?rs\.?" + AMOUNT, flat)
    f["sanctioned_amount"] = _money(m.group(1)) if m else None
    m = re.search(r"workstatus:?\(completed/?inprogress\)(completed|inprogress)", flat)
    f["status"] = m.group(1) if m else None
    f["payments"] = [(to_date(d), _money(a)) for d, a in re.findall(
        r"paymentapprovaldate:?" + DATE + r".{0,60}?approvedamount:?rs\.?" + AMOUNT, flat)]
    if not f["payments"]:
        d = re.search(r"paymentapprovaldate:?" + DATE, flat)
        a = re.search(r"approvedamount:?rs\.?" + AMOUNT, flat)
        if d or a:
            f["payments"] = [(to_date(d.group(1)) if d else None, _money(a.group(1)) if a
                              else None)]
    code = next((VENDOR_CODE.search(r["text"]) for r in lines if VENDOR_CODE.search(r["text"])),
                None)
    f["vendor_code"] = code.group(0) if code else None
    f["page"] = page.get("page")
    return f


def parse_uc_p2(page: dict) -> dict | None:
    """The certification paragraph: sanction date and amount again, and whether the officer
    marked any of its boxes."""
    text = " ".join(zeros_in_numbers(r["text"]) for r in ordered_lines(page))
    flat = squash(text)
    out = {}
    if "havingbeenfullysatisfied" in flat:
        out["boxes_marked"] = any(b.strip() for b in re.findall(r"\[([^\]]{0,3})\]", text))
    m = re.search(r"sanctionedon" + DATE, flat)
    if m:
        a = re.search(r"outofrs\.?" + AMOUNT, flat)
        out["sanction_date"] = to_date(m.group(1))
        out["amount"] = _money(a.group(1)) if a else None
    return out or None


def read_file(pages: list[dict]) -> dict:
    """Everything the reader takes from one file: its page kinds, certificates (with a sanction
    date the first page lost filled from the certification paragraph) and certification
    pages."""
    kinds = [page_kind(p) for p in pages]
    certs = [c for p in pages if (c := parse_uc(p))]
    p2 = [x for p in pages if (x := parse_uc_p2(p))]
    for c in certs:
        if c["sanction_date"] is None:
            same = [x for x in p2 if x.get("sanction_date")
                    and x.get("amount") == c["sanctioned_amount"]]
            dated = [x for x in p2 if x.get("sanction_date")]
            pick = same or (dated if len(dated) == 1 else [])
            if pick:
                c["sanction_date"], c["sanction_date_from"] = pick[0]["sanction_date"], \
                    "certification"
    readable = [k for k in kinds if k not in ("other_or_unreadable", "photo_or_blank")]
    return {"kinds": kinds, "readable": bool(readable), "certificates": certs,
            "certification_pages": [x for x in p2 if "boxes_marked" in x]}
