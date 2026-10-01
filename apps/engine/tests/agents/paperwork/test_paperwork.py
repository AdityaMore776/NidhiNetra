"""Paperwork (T110): the certificate reader on synthetic OCR pages with the real form's layout,
and the checks against the portal record. No real names, phones or account numbers."""

from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.paperwork.agent import assess, own_certificates
from drishti.agents.paperwork.reader import page_kind, parse_uc, read_file
from drishti.agents.paperwork.vendors import VendorIndex


def _page(lines: list[str], page: int = 1) -> dict:
    # one OCR box per printed line, 30 px apart, as rapidocr returns them
    return {"page": page, "lines": [[[[10, 30 * i], [600, 30 * i], [600, 30 * i + 20],
                                      [10, 30 * i + 20]], t, 0.95] for i, t in enumerate(lines)]}


UC = _page([
    "Annexure-VI", "UTILIZATION CERTIFICATE",
    "Implementing Agency : BLOCK OFFICE TEST",
    "Name of Work : CC road at Sitapur",
    "Location of Work : Sitapur",
    "Sanction Date of the work by the District Authority : 20/03/2024",
    "Total Sanctioned Amount for the Work : Rs. 3,00,000",
    "Work Status (Completed/In progress) In progress",
    "Payment Approval Date : 15/07/2024",
    "Approved Amount : Rs. 2,98,500",
    "TEST VENDOR V123456789012",
])
CERT_P2 = _page(["Certified that out of Rs. 3,00,000 of grants-in-aid of MPLADS scheme "
                 "sanctioned on 20/03/2024 by the District Authority",
                 "having been fully satisfied [ ] [ ]"], page=2)


def _work(**kw):
    w = {"work_id": "W1", "description": "Construction of CC road at Sitapur village",
         "amount": 298_500.0, "status": "COMPLETED", "recommended_date": date(2024, 1, 1),
         "district_lgd": "162"}
    w.update(kw)
    return w


def _evidence(*certs, cert_pages=({"boxes_marked": False},), readable=True):
    return {"files": [{"id": "1.2", "ext": "pdf", "pages": 2, "readable": readable,
                       "certificates": list(certs), "certification_pages": list(cert_pages)}]}


def _cert(**kw):
    c = {"sanction_date": "2024-03-20", "sanctioned_amount": 300_000.0, "status": "inprogress",
         "payments": [["2024-07-15", 298_500.0]], "vendor_code": "V123456789012",
         "location": "Sitapur"}
    c.update(kw)
    return c


def test_reader_reads_the_typed_fields_and_never_the_vendor_name():
    f = parse_uc(UC)
    assert page_kind(UC) == "utilisation_certificate"
    assert f["sanction_date"] == date(2024, 3, 20) and f["sanctioned_amount"] == 300_000.0
    assert f["status"] == "inprogress" and f["vendor_code"] == "V123456789012"
    assert f["payments"] == [(date(2024, 7, 15), 298_500.0)]
    assert "vendor_name" not in f and "TEST VENDOR" not in str(f)


def test_a_sanction_date_the_first_page_lost_comes_from_the_certification_paragraph():
    first = _page([x for _b, x, _c in UC["lines"] if not x.startswith("Sanction Date")])
    r = read_file([first, CERT_P2])
    assert r["certificates"][0]["sanction_date"] == date(2024, 3, 20)
    assert r["certificates"][0]["sanction_date_from"] == "certification"
    assert r["certification_pages"] == [{"boxes_marked": False, "sanction_date": date(2024, 3, 20),
                                         "amount": 300_000.0}]


def test_late_sanction_is_graded_and_leaves_out_election_pauses():
    # 1 Jan -> 20 Mar 2024 is 79 days; 5 of them fall in the 2024 election pause -> 74: in time
    r = assess(_work() | {"evidence": _evidence(_cert())})
    assert "SANCTION_LATE" not in {f.code for f in r.findings}
    r2 = assess(_work(recommended_date=date(2023, 6, 1)) | {"evidence": _evidence(_cert())})
    f2 = next(f for f in r2.findings if f.code == "SANCTION_LATE")
    assert 0.30 < f2.risk <= 0.60 and "para 3.12" in f2.text


def test_sanction_dated_before_the_recommendation_needs_checking():
    r = assess(_work(recommended_date=date(2024, 5, 1)) | {"evidence": _evidence(_cert())})
    assert r.verdict == "SANCTIONED_BEFORE_RECOMMENDATION" and not r.hard


def test_an_instalment_certificate_is_a_note_and_a_repeated_page_counts_once():
    part = _cert(payments=[["2024-07-15", 100_000.0]])
    r = assess(_work(recommended_date=date(2024, 3, 1)) | {"evidence": _evidence(part, part)})
    f = next(f for f in r.findings if f.code == "PART_PAYMENT_PAPERS_ONLY")
    assert f.risk == pytest.approx(0.05) and "Rs 1.00 lakh (34%)" in f.text


def test_more_paid_on_paper_than_on_the_portal_is_a_finding():
    more = _cert(payments=[["2024-07-15", 298_500.0], ["2024-09-01", 120_000.0]])
    r = assess(_work(recommended_date=date(2024, 3, 1)) | {"evidence": _evidence(more)})
    assert r.verdict == "PAID_MORE_ON_PAPER" and r.risk == pytest.approx(0.30)


def test_another_works_papers_and_a_file_of_several_works():
    other = _cert(sanctioned_amount=900_000.0, payments=[["2024-07-15", 900_000.0]],
                  location="Rampur")
    r = assess(_work() | {"evidence": _evidence(other)})
    assert r.verdict == "OTHER_WORKS_PAPERS"
    a, b = _cert(location="Malakpur"), _cert(location="Sherpur")
    w = _work(description="High mast light in my constituency")
    assert len(own_certificates([a, b], w)) == 2
    r = assess(w | {"evidence": _evidence(a, b)})
    assert "PAPERS_OF_SEVERAL_WORKS" in {f.code for f in r.findings}
    assert "PAID_MORE_ON_PAPER" not in {f.code for f in r.findings}


def test_completed_on_the_portal_in_progress_on_paper_is_only_a_note():
    r = assess(_work(recommended_date=date(2024, 3, 1)) | {"evidence": _evidence(_cert())})
    f = next(f for f in r.findings if f.code == "STILL_IN_PROGRESS_ON_PAPER")
    assert f.risk == pytest.approx(0.05)
    assert "CERTIFICATION_BLANK" in {f.code for f in r.findings}


def test_vendor_concentration_is_a_fact_that_only_joins_another_finding():
    works = [_work(work_id=f"W{i}") | {"evidence": _evidence(_cert())} for i in range(12)]
    vendors = VendorIndex.build(works)
    assert vendors.share("162", "V123456789012") == (1.0, 12)
    quiet = assess(_work(recommended_date=date(2024, 3, 1)) | {"evidence": _evidence(_cert())},
                   vendors)
    assert "VENDOR_CONCENTRATION" not in {f.code for f in quiet.findings}
    assert quiet.evidence["vendors"][0]["district_share"] == 1.0
    loud = assess(_work(recommended_date=date(2023, 6, 1)) | {"evidence": _evidence(_cert())},
                  vendors)
    assert "VENDOR_CONCENTRATION" in {f.code for f in loud.findings}


def test_no_papers_is_not_applicable_and_unreadable_papers_not_assessable():
    assert assess(_work()).status == Status.NOT_APPLICABLE
    photo_only = {"files": [{"id": "9", "ext": "jpg", "readable": False}]}
    assert assess(_work() | {"evidence": photo_only}).status == Status.NOT_APPLICABLE
    unread = assess(_work() | {"evidence": _evidence(readable=False)})
    assert unread.status == Status.NOT_ASSESSABLE and "not a clean chit" in unread.headline
