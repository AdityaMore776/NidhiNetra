"""Cost (T135, the robustness loop: data/trial/agent_robustness_loop.py): what the loop broke and
how it stays fixed. Price data that cannot be trusted switches that price off and is recorded as a
gap (never guessed); padding moved out of the priced lines, items no reader knows, a warning left
unanswered and one agency's many forms no longer get past the check or skew it."""

from __future__ import annotations

import copy

from drishti.agents.cost_estimate import rates, whole
from drishti.cost_form import materials, pswif
from drishti.cost_form.validate import validate
from tests.agents.cost_estimate.test_whole_estimate import (
    SOR,
    TODAY,
    _others,
    codes,
    priced,
    run,
)
from tests.cost_form.test_pswif import road


def test_one_agency_filing_many_forms_counts_once():
    # ten forms from one agency at 70% cannot drag the district's rate down
    cheap = _others(10, 1, factor=0.7)
    for w in cheap:
        w["cost_form_meta"]["saved_by"] = "cheap-agency"
        w["work_id"] = "C" + w["work_id"]
    idx = rates.RateIndex.build(_others(6, 3) + cheap)
    rate, forms, agencies = idx.district_rate("T|BETA", "sand", "agency-X", "W1", TODAY)
    assert agencies == 4 and forms == 16
    assert rate == 2500                           # the honest agencies' rate, not 70% of it
    assert "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(run(priced(), sor=None, index=idx))


def test_agencies_that_disagree_give_no_rate_and_a_gap():
    works = []
    for k, f in enumerate((0.5, 1.7, 0.6, 1.8, 0.55, 1.6)):
        works += [{**w, "work_id": f"S{k}", "cost_form_meta": {"saved_by": f"agency-{k}"}}
                  for w in _others(1, 1, factor=f)]
    idx = rates.RateIndex.build(works)
    assert idx.district_rate("T|BETA", "sand", "agency-X", "W1", TODAY) is None
    fair, gap = idx.price("T|BETA", None, "sand", "agency-X", "W1", TODAY)
    assert fair is None and gap.reason == "too_spread" and gap.spread > rates.MAX_SPREAD
    r = run(priced(), sor=None, index=idx)
    assert "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(r)
    assert any(g["reason"] == "too_spread" for g in r.evidence["data_gaps"])
    assert any("disagree" in lim for lim in r.limitations)


def test_each_gap_says_why():
    few = rates.RateIndex.build(_others(3, 3))
    old = rates.RateIndex.build(_others(6, 3, month="2025-01"))
    none = rates.RateIndex.build([])
    for idx, reason in ((few, "too_few"), (old, "too_old"), (none, "none")):
        fair, gap = idx.price("T|BETA", None, "cement", "agency-X", "W1", TODAY)
        assert fair is None and gap.reason == reason and gap.text()


def test_a_district_without_enough_forms_is_priced_from_the_state_more_leniently():
    others = []
    for k in range(8):
        f = priced()
        f["timing"]["estimate_month"] = "2026-08"
        others.append({"work_id": f"G{k}", "district_lgd": "T|GAMMA", "state_name": "Testland",
                       "cost_form": f, "cost_form_meta": {"saved_by": f"agency-{k % 4}"}})
    idx = rates.RateIndex.build(others)
    fair, gap = idx.price("T|BETA", "testland", "sand", "agency-X", "W1", TODAY)
    assert fair[1] == "state" and fair[0] == 2500 * (1 + rates.STATE_ALLOWANCE)
    assert gap.reason == "none"          # recorded: the district itself has no forms yet


def test_name_variants_are_one_agency():
    keys = {rates.agency_key(n) for n in ("Gramin Path Nigam, Div-1", "GRAMIN PATH NIGAM "
                                          "(Division 2)", "Gramin Path Nigam Div. 3",
                                          "Gramin-Path-Nigam")}
    assert len(keys) == 1
    assert rates.agency_key("Jal Nigam") != rates.agency_key("Gramin Path Nigam")


def test_an_unanswered_typo_warning_holds_its_line_and_judges_the_rest():
    f = priced(1.3)                             # every line padded 30%
    f["sites"][0]["lines"].append({"group": "materials", "item": "Cement for the kerbs",
                                   "material_id": "cement", "unit": "bag", "quantity": 10,
                                   "rate": 4000, "basis": "market_rate"})   # an extra zero?
    f["totals"]["total_as_per_document"] = validate(f, today=TODAY)["computed"]["grand_total"]
    f["recommendation"]["mp_amount"] = f["totals"]["total_as_per_document"]
    r = run(f)
    assert r.evidence["held_lines"] == [(0, len(f["sites"][0]["lines"]) - 1)]
    assert "ESTIMATE_ABOVE_FAIR_PRICE" in codes(r)          # the other lines still judged
    assert any("typing mistake" in lim for lim in r.limitations)


def test_padding_moved_into_a_lump_sum_or_other_charges_is_still_counted():
    for where in ("lump", "other"):
        f = priced()
        lines_total = validate(f, today=TODAY)["computed"]["lines_total"]
        extra = round(0.30 * lines_total)
        if where == "lump":
            f["sites"][0]["lines"].append({"group": "other", "item": "Miscellaneous works",
                                           "unit": "ls", "amount": extra, "basis": "other",
                                           "basis_other": "estimate"})
        else:
            f["charges"]["other_fees_amount"] = extra
        f["confirmed"] = [i["key"] for i in validate(f, today=TODAY)["issues"]
                          if i["level"] == "confirm"]
        total = validate(f, today=TODAY)["computed"]["grand_total"]
        f["totals"]["total_as_per_document"] = total
        f["recommendation"]["mp_amount"] = total
        r = run(f)
        assert "ESTIMATE_ABOVE_FAIR_PRICE" in codes(r), where
        assert r.evidence["whole"]["unexplained"], where


def test_a_small_lump_sum_and_gst_in_other_charges_are_honest():
    f = priced()
    lines_total = validate(f, today=TODAY)["computed"]["lines_total"]
    ls = sum(ln.get("amount") or 0 for ln in f["sites"][0]["lines"] if ln.get("unit") == "ls")
    top_up = round(0.0199 * lines_total - ls)              # lump sums up to 2% of the lines
    f["sites"][0]["lines"].append({"group": "other", "item": "Signage and sundries",
                                   "unit": "ls", "amount": top_up,
                                   "basis": "other", "basis_other": "estimate"})
    del f["charges"]["gst_percent"], f["charges"]["gst_amount"]    # GST not on the form...
    f["charges"]["other_fees_amount"] = round(0.18 * lines_total)  # ...but in "other"
    total = validate(f, today=TODAY)["computed"]["grand_total"]
    f["totals"]["total_as_per_document"] = total
    f["recommendation"]["mp_amount"] = total
    w = whole.unexplained(f, validate(f, today=TODAY)["computed"], civil=True)
    assert w == {}
    assert "ESTIMATE_ABOVE_FAIR_PRICE" not in codes(run(f))


def test_items_no_reader_knows_in_a_construction_estimate_are_asked_about():
    f = priced()
    for ln in f["sites"][0]["lines"][:4]:
        # an item no reader knows (T144: "Base course material", used before, now reads as the
        # road's base)
        ln["item"], ln["material_id"] = "Site works as per drawing", None
    f["confirmed"] = [i["key"] for i in validate(f, today=TODAY)["issues"]
                      if i["level"] == "confirm"]
    r = run(f)
    assert "ESTIMATE_NOT_ITEMISED" in codes(r)
    # recognisable items the agency left unconfirmed are itemised, only not priced
    g = priced()
    for ln in g["sites"][0]["lines"]:
        ln["material_id"] = None
    assert "ESTIMATE_NOT_ITEMISED" not in codes(run(g))


def test_trade_words_for_sand_and_stone_are_read():
    for item, mat in (("Fine aggregate (sand)", "sand"), ("Coarse aggregate 20 mm", "aggregate"),
                      ("Kapchi 20", "aggregate"), ("Rodi 40 mm", "aggregate"),
                      ("20mm jelly", "aggregate"), ("Badarpur", "sand")):
        assert materials.match(item) == mat, item


def test_a_website_filing_with_a_lump_sum_can_be_judged():
    # T135: the adapter's lump-sum line had no source, so such a filing was never ready
    f = pswif.to_cost_form(road(lumpsum_components="25000"), TODAY)
    fixes = [i for i in validate(f, today=TODAY)["issues"] if i["level"] == "fix"]
    assert not [i for i in fixes if "basis_other" in i["field"]]


def test_a_gap_never_changes_with_the_form_of_the_data():
    # junk in other agencies' forms never breaks the index or the gap
    junk = copy.deepcopy(_others(6, 3))
    junk[0]["cost_form"]["sites"][0]["lines"][0]["rate"] = float("inf")
    junk[1]["cost_form"]["sites"] = "junk"
    junk[2]["cost_form"]["sites"][0]["lines"][1]["unit"] = {"a": 1}
    idx = rates.RateIndex.build(junk)
    assert idx.price("T|BETA", None, "cement", "agency-X", "W1", TODAY)
    assert rates.coverage(idx, "T|BETA", None, TODAY, SOR)


def test_a_size_the_forms_own_scope_contradicts_is_asked_about():
    from types import SimpleNamespace

    from drishti.agents.cost_estimate import agent

    def check(**over):
        f = pswif.to_cost_form(road(**over), TODAY)
        total = validate(f, today=TODAY)["computed"]["grand_total"]   # the estimate's own total
        f["totals"]["total_as_per_document"] = f["recommendation"]["mp_amount"] = total
        work = {"work_id": "W1", "state_name": "Uttar Pradesh", "district_name": "Jaunpur",
                "district_lgd": "181", "cost_form": f}
        return codes(agent.assess(work, SimpleNamespace(as_of=TODAY, data={"sor": None})))

    # twice the cement, "justified" by a 7 m width the scope (3.5 m wide) never states
    wide = check(road_width_m="7", boq_qty_1="2200", boq_just_1="Wider road")
    assert "SIZE_NOT_AS_DESCRIBED" in wide and "MATERIAL_QUANTITY_ABOVE_SIZE" not in wide
    # the same, with the scope saying 7 m too: the agency's word, checked at the site instead
    same = check(road_width_m="7", boq_qty_1="2200", boq_just_1="Wider road",
                 scope_of_work=road()["scope_of_work"].replace("3.5 m wide", "7 m wide"))
    assert "SIZE_NOT_AS_DESCRIBED" not in same
    # an honest road whose scope and size agree
    assert "SIZE_NOT_AS_DESCRIBED" not in check()
