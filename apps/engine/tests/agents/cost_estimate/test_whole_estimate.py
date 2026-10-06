"""Cost (T121, plan T120 §6): every line against its fair rate, then the whole estimate.

"One costly line can be honest; every line a little costly is a pattern." The planted cases: an
honest estimate at the fair rates is FAIR; every rate a little high adds up to a question; one
high line alone does not; a small work's gap under Rs 50,000 is never asked; a line citing an SoR
code is held to that code's rate; district rates count only with 5+ forms from 3+ other agencies
in the last 6 months, never the agency's own, and are capped by the SoR."""

from __future__ import annotations

import copy
from datetime import date
from types import SimpleNamespace

import pytest

from drishti.agents.contract import Status, check_plain_language
from drishti.agents.cost_estimate import agent, rates, whole
from drishti.cost_form.validate import validate
from tests.cost_form.test_cost_form import road_form

TODAY = date(2026, 10, 3)
IDS = ["cement", "sand", "aggregate", "granular_base", "labour_unskilled", "labour_skilled"]
SOR = {"state": "Testland", "edition": "Test SoR 2026", "source": "made up for tests",
       "items": {"UP-PWD 5.3": {"material_id": "aggregate", "unit": "m3", "rate": 3000},
                 "UP-PWD 4.1": {"material_id": "granular_base", "unit": "m3", "rate": 1500},
                 "UP-LAB-1": {"material_id": "labour_unskilled", "unit": "day", "rate": 450},
                 "UP-LAB-2": {"material_id": "labour_skilled", "unit": "day", "rate": 800}},
       "materials": {"cement": {"unit": "bag", "rate": 400}, "sand": {"unit": "m3", "rate": 2500},
                     "aggregate": {"unit": "m3", "rate": 3000},
                     "granular_base": {"unit": "m3", "rate": 1500},
                     "labour_unskilled": {"unit": "day", "rate": 450},
                     "labour_skilled": {"unit": "day", "rate": 800}}}


def priced(factor: float = 1.0, by: dict | None = None, qty: dict | None = None,
           scale: float = 1.0) -> dict:
    """The 250 m CC road with its six material and labour lines confirmed, every rate times
    `factor` (or `by[material]`), quantities times `qty[material]`, no charges, totals right."""
    f = road_form()
    by, qty = by or {}, qty or {}
    for ln, m in zip(f["sites"][0]["lines"], IDS, strict=False):
        ln["material_id"] = m
        ln["rate"] = round(ln["rate"] * by.get(m, factor), 2)
        ln["quantity"] = round(ln["quantity"] * qty.get(m, 1.0) * scale, 3)
        if ln["group"] == "labour":              # person-days = workers x days (T141)
            ln["days"] = ln["quantity"] / ln["workers"]
    for ln in f["sites"][0]["lines"][6:]:
        if "amount" in ln:
            ln["amount"] = round(ln["amount"] * scale, 2)
        else:
            ln["quantity"] = round(ln["quantity"] * scale, 3)
    f["sites"][0]["size"]["length_m"] = 250 * scale
    f["sites"][0]["location"]["end_lat"] = 25.75 + 0.002 * scale       # the ends fit the length
    if qty.get("cement", 1.0) > 1.0:                                    # the agency confirmed it
        f["confirmed"] = ["more_than_size_needs:sites[0].lines[0].quantity"]
    f["charges"] = {"contingency_percent": 0, "gst_percent": 0, "gst_amount": 0,
                    "labour_cess_amount": 0, "royalty_amount": 0, "other_fees_amount": 0}
    total = validate(f, today=TODAY)["computed"]["grand_total"]
    f["totals"] = {"total_as_per_document": total}
    f["recommendation"]["mp_amount"] = total
    assert validate(f, today=TODAY)["ready"]
    return f


def run(form, sor=SOR, index=None, work_id="W1", saved_by="agency-A"):
    work = {"work_id": work_id, "state_name": "Testland", "district_name": "Beta",
            "district_lgd": "T|BETA", "cost_form": form,
            "cost_form_meta": {"saved_by": saved_by}}
    ctx = SimpleNamespace(as_of=TODAY, data={"sor": sor, "rates": index})
    return agent.assess(work, ctx)


def codes(r):
    return [f.code for f in r.findings]


def test_an_estimate_at_the_fair_rates_is_fair():
    r = run(priced())
    assert r.status == Status.ASSESSED and "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(r)
    w = r.evidence["whole"]
    assert w["verdict"] == "FAIR" and w["gap"] == pytest.approx(0, abs=1)
    assert w["coverage"] > 0.9 and w["priced_lines"] == 6


def test_every_rate_a_little_high_adds_up_to_a_question():
    r = run(priced(1.30))
    f = next(f for f in r.findings if f.code == "ESTIMATE_ABOVE_FAIR_PRICE")
    assert f.risk == agent.WHOLE_RISK and f.evidence["gap_share"] > whole.GAP_SHARE
    # the labour rows cite schedule items, so they are held to them like any line (T141)
    assert "6 of the 6 priced lines are above their fair rate" in f.text
    assert "Most of the gap" in f.text and "Needs checking before sanction" in f.text
    check_plain_language(f.text)
    assert f.evidence["message_hi"]


def test_ten_percent_on_every_line_stays_within_the_fair_band():
    assert "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(run(priced(1.10)))


def _uncoded(form: dict) -> dict:
    """The labour rows priced at the market, citing no schedule item."""
    for ln in form["sites"][0]["lines"]:
        if ln["group"] == "labour":
            ln["basis"] = "market_rate"
            ln.pop("sor_code", None)
    return form


def test_labour_a_little_high_adds_nothing_to_the_whole():
    # T141, the owner: labour is asked about only when blatant (twice its trade's rate)
    w = run(_uncoded(priced(by={"labour_unskilled": 1.5, "labour_skilled": 1.5})))
    assert w.evidence["whole"]["gap"] == pytest.approx(0, abs=1)
    assert w.evidence["whole"]["above_fair_rate"] == 0
    w = run(_uncoded(priced(by={"labour_skilled": 2.2}))).evidence["whole"]
    assert w["above_fair_rate"] == 1 and w["gap"] > 0
    # a row citing a schedule item is held to that item's rate: a fact, not a judgement
    w = run(priced(by={"labour_unskilled": 1.5})).evidence["whole"]
    assert w["above_fair_rate"] == 1 and w["gap"] > 0


def test_one_costly_line_alone_is_not_a_question():
    # sand at 1.6x is Rs 1.05 lakh extra on Rs 18.8 lakh: 6%
    r = run(priced(by={"sand": 1.6}))
    assert "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(r)
    assert r.evidence["whole"]["above_fair_rate"] == 1


def test_a_small_works_gap_under_rs_50000_is_never_asked():
    small = priced(1.25, scale=0.1)              # a 25 m road: 25% but about Rs 44,000
    w = run(small).evidence["whole"]
    assert w["gap_share"] > whole.GAP_SHARE and w["gap"] < whole.GAP_MIN_RS
    assert w["verdict"] == "FAIR"


def test_extra_quantity_counts_in_the_gap():
    # cement at 1.5x what the 250 m x 3.75 m x 150 mm slab needs (plus 10% tolerance)
    r = run(priced(by={"sand": 1.2, "aggregate": 1.2}, qty={"cement": 1.6}))
    f = next(f for f in r.findings if f.code == "ESTIMATE_ABOVE_FAIR_PRICE")
    assert "cement" in f.text and "where the size needs" in f.text
    # a confirmed quantity far beyond the size stays its own question as well
    assert "MATERIAL_QUANTITY_ABOVE_SIZE" in codes(r)


def test_a_confirmed_quantity_far_beyond_the_size_is_asked_even_when_the_total_is_fair():
    r = run(priced(qty={"cement": 1.6}))
    assert r.evidence["whole"]["verdict"] == "FAIR"
    assert "MATERIAL_QUANTITY_ABOVE_SIZE" in codes(r)


def test_a_line_citing_an_sor_code_is_held_to_that_codes_rate():
    form = priced(by={"aggregate": 1.6, "granular_base": 1.6, "labour_unskilled": 1.3})
    f = next(f for f in run(form).findings if f.code == "ESTIMATE_ABOVE_FAIR_PRICE")
    assert "cites SoR item UP-PWD 5.3" in f.text and "Rs 3,000" in f.text


def test_without_any_fair_rate_the_whole_is_not_judged():
    r = run(priced(1.3), sor=None)               # only cement's need is known: about a quarter
    assert r.evidence["whole"]["verdict"] == "CANT_CHECK"
    assert "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(r)
    assert any("whole estimate was not judged" in lim for lim in r.limitations)
    assert any("Schedule of Rates is not loaded" in lim for lim in r.limitations)


# --- district rates -----------------------------------------------------------------------

def _others(n_forms: int, agencies: int, factor: float = 1.0, month: str = "2026-08"):
    works = []
    for k in range(n_forms):
        f = priced(factor)
        f["timing"]["estimate_month"] = month
        works.append({"work_id": f"O{k}", "district_lgd": "T|BETA", "cost_form": f,
                      "cost_form_meta": {"saved_by": f"agency-{k % agencies}"}})
    return works


def test_district_rates_count_with_five_forms_from_three_other_agencies():
    idx = rates.RateIndex.build(_others(5, 3))
    assert idx.district_rate("T|BETA", "sand", "agency-X", "W1", TODAY)[1:] == (5, 3)
    r = run(priced(1.25), sor=None, index=idx)
    assert "ESTIMATE_ABOVE_FAIR_PRICE" in codes(r)
    assert any("other agencies" in s for s in r.evidence["whole"]["sources"])


def test_too_few_forms_or_agencies_give_no_district_rate():
    assert rates.RateIndex.build(_others(4, 3)).district_rate(
        "T|BETA", "sand", "agency-X", "W1", TODAY) is None
    assert rates.RateIndex.build(_others(6, 2)).district_rate(
        "T|BETA", "sand", "agency-X", "W1", TODAY) is None


def test_an_agency_never_counts_in_its_own_baseline():
    idx = rates.RateIndex.build(_others(6, 3))
    # agency-0 wrote two of the six: without them, 4 forms remain
    assert idx.district_rate("T|BETA", "sand", "agency-0", "W1", TODAY) is None


def test_old_forms_do_not_count():
    idx = rates.RateIndex.build(_others(6, 3, month="2025-12"))
    assert idx.district_rate("T|BETA", "sand", "agency-X", "W1", TODAY) is None


def test_the_sor_caps_a_district_that_raised_its_rates_together():
    idx = rates.RateIndex.build(_others(6, 3, factor=1.5))
    form = priced(1.4)
    w = run(form, index=idx).evidence["whole"]
    # without the cap the district's own 1.5x would make 1.4x look cheap
    assert w["verdict"] == "ASK"
    line = next(x for x in w["lines"] if x["material"] == "sand")
    assert line["fair_rate"] == pytest.approx(2500 * (1 + rates.SOR_ALLOWANCE))


def test_damaged_lines_never_break_the_whole():
    form = priced(1.2)
    bad = copy.deepcopy(form)
    bad["sites"][0]["lines"] += [{"material_id": "cement", "quantity": "x", "unit": "bag",
                                  "rate": None}, "junk", {"material_id": 7}]
    w = whole.judge(bad, validate(form, today=TODAY)["computed"], "ROAD_CC", SOR, None,
                    "T|BETA", "a", "W1", TODAY)
    assert w.verdict in ("ASK", "FAIR", "CANT_CHECK")


def test_a_padded_line_written_in_a_unit_that_does_not_fit_is_not_a_way_out():
    # the robustness loop (T141): cement in "nos", left unanswered, took the estimate under the
    # coverage it needs, and the padding on every other line went unjudged
    form = priced(by={"cement": 1.3, "sand": 1.3, "aggregate": 1.3, "granular_base": 1.3})
    form["sites"][0]["lines"][0]["unit"] = "nos"
    form["sites"][0]["lines"][0].pop("material_id")
    r = run(form)
    assert r.evidence["held_lines"] == [(0, 0)]
    assert "ESTIMATE_ABOVE_FAIR_PRICE" in codes(r)
    # the held line itself is never the question: an honest unit slip stays at its own value
    honest = priced()
    honest["sites"][0]["lines"][0]["unit"] = "nos"
    honest["sites"][0]["lines"][0].pop("material_id")
    w = run(honest).evidence["whole"]
    assert w["verdict"] == "FAIR" and not w["unexplained"]
