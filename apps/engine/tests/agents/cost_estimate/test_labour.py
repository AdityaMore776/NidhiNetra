"""Labour, trade by trade (T141). The owner: only blatant irregularities, never "it could be done
with fewer workers". So a trade's day rate far above what others pay THAT trade here is asked, and
workers kept on site longer than the work lasts; how many workers, or days within the work's time,
never is. A row is judged as its trade, never the grade it declares."""

from __future__ import annotations

import copy
import random
from datetime import date
from types import SimpleNamespace

import pytest

from drishti.agents.contract import Status, check_plain_language
from drishti.agents.cost_estimate import agent, labour, rates
from drishti.cost_form import catalog, materials
from drishti.cost_form.validate import validate
from tests.cost_form.test_cost_form import road_form

TODAY = date(2026, 10, 3)
# what six other agencies in the district pay each trade (Rs a day)
PEERS = {"labour_mason": [760, 800, 820, 780, 850, 800],
         "labour_beldar": [430, 450, 440, 460, 420, 450],
         "labour_helper": [440, 460, 450, 470, 430, 450],
         "labour_carpenter": [780, 820, 800, 790, 840, 810],
         "labour_operator": [900, 950, 1000, 920, 980, 940]}
MASON, BELDAR = 5, 4                          # the road form's labour rows


def index(peers=PEERS, district="T|BETA") -> rates.RateIndex:
    works = []
    for a in range(len(next(iter(peers.values())))):
        lines = [{"group": "labour", "material_id": m, "rate": r[a], "unit": "day",
                  "quantity": 100} for m, r in peers.items()]
        works.append({"work_id": f"P{a}", "district_lgd": district, "state_name": "Testland",
                      "cost_form_meta": {"saved_by": f"peer-{a}"},
                      "cost_form": {"timing": {"estimate_month": "2026-09"},
                                    "sites": [{"lines": lines}]}})
    return rates.RateIndex.build(works)


def filed(f: dict) -> dict:
    """The form with its totals and the MP's amount made to agree (so only labour differs)."""
    f["charges"] = {"contingency_percent": 0, "gst_percent": 0, "gst_amount": 0,
                    "labour_cess_amount": 0, "royalty_amount": 0, "other_fees_amount": 0}
    total = validate(f, today=TODAY)["computed"]["grand_total"]
    f["totals"] = {"total_as_per_document": total}
    f["recommendation"]["mp_amount"] = total
    return f


def labour_row(trade, workers, days, rate, activity="Brick and plaster work on the walls",
               **extra) -> dict:
    return {"group": "labour", "item": (catalog.material(trade) or {}).get("label", "Karigar"),
            "material_id": trade, "workers": workers, "days": days, "unit": "day",
            "rate": rate, "basis": "market_rate", "activity": activity, **extra}


def with_rows(*rows, edit=None) -> dict:
    f = road_form()
    lines = f["sites"][0]["lines"]
    for r in rows:
        lines.append(r)
    if edit:
        edit(lines)
    return filed(f)


def run(form, idx=None, sor=None):
    work = {"work_id": "W1", "state_name": "Testland", "district_name": "Beta",
            "district_lgd": "T|BETA", "cost_form": form,
            "cost_form_meta": {"saved_by": "agency-A"}}
    ctx = SimpleNamespace(as_of=TODAY, data={"sor": sor, "rates": idx if idx else index()})
    return agent.assess(work, ctx)


def codes(r) -> set[str]:
    return {f.code for f in r.findings}


def issues(form) -> dict[str, dict]:
    return {i["code"]: i for i in validate(form, today=TODAY)["issues"]}


def set_rate(j, rate):
    def edit(lines):
        lines[j]["rate"] = rate
    return edit


# ---- the trades ------------------------------------------------------------------------------

@pytest.mark.parametrize("typed,expected", [
    ("Mason", "labour_mason"), ("Raj mistri", "labour_mason"), ("राजमिस्त्री", "labour_mason"),
    ("Skilled mason", "labour_mason"), ("Semi skilled helper", "labour_helper"),
    ("Mason helper", "labour_helper"), ("Beldar", "labour_beldar"), ("मजदूर", "labour_beldar"),
    ("JCB operator", "labour_operator"), ("Bijli mistri", "labour_electrician"),
    ("Badhai", "labour_carpenter"), ("Skilled labour", "labour_skilled"),
    ("Labour for curing", "labour_unskilled"), ("Karigar", None),
])
def test_a_trade_is_recognised_by_its_own_name(typed, expected):
    assert materials.match(typed, labour=True) == expected


def test_a_labour_row_reads_as_a_trade_and_a_machine_as_a_machine():
    assert materials.match("Painter for distemper") == "paint"            # words alone
    assert materials.match("Painter for distemper", labour=True) == "labour_painter"
    assert materials.match("JCB with operator", labour=False) is None


def test_every_trade_has_a_grade_and_every_grade_a_generic_entry():
    for m in catalog.materials():
        if m.get("trade") or m.get("generic"):
            assert m["grade"] in catalog.GRADES and m["units"] == ["day"], m
    assert all(catalog.grade_entry(g) for g in catalog.GRADES)


# ---- the form: mistakes refused on the agency's screen -----------------------------------------

def test_the_honest_road_form_with_its_labour_table_is_ready():
    assert validate(filed(road_form()), today=TODAY)["ready"]


def test_person_days_must_be_workers_times_days():
    f = with_rows(edit=lambda ln: ln[MASON].update(quantity=300))
    assert issues(f)["labour_arithmetic"]["level"] == "fix"


def test_person_days_left_out_are_worked_out():
    f = road_form()
    del f["sites"][0]["lines"][MASON]["quantity"]
    f = filed(f)
    assert validate(f, today=TODAY)["ready"]
    assert validate(f, today=TODAY)["computed"]["lines_total"] == 1_876_000


@pytest.mark.parametrize("change,code", [
    ({"workers": 2.5}, "labour_workers_whole"),
    ({"unit": "month"}, "labour_unit"),
    ({"workers": 0}, "impossible"),
    ({"activity": "work"}, "too_short"),
    ({"material_id": ""}, "labour_trade_needed"),
    ({"material_id": "none"}, "labour_grade_needed"),
    ({"material_id": "cement"}, "labour_not_a_trade"),
    ({"for_lines": ["one"]}, "not_a_list"),
    ({"for_lines": [42]}, "labour_line_unknown"),
])
def test_a_labour_slip_is_fixed_before_submitting(change, code):
    f = with_rows(edit=lambda ln: ln[MASON].update(change))
    found = issues(f)
    assert code in found and found[code]["level"] == "fix", found.keys()


def test_another_trade_with_its_grade_is_accepted():
    f = with_rows(labour_row("none", 2, 20, 700, grade="skilled"))
    assert validate(f, today=TODAY)["ready"]


def test_a_grade_above_the_trade_is_asked_to_confirm_and_changes_nothing():
    f = with_rows(labour_row("labour_helper", 4, 40, 460, grade="highly_skilled"))
    assert issues(f)["labour_grade_above_trade"]["level"] == "confirm"


def test_labour_cannot_be_paid_inside_a_composite_rate_and_again():
    def composite(lines):
        lines[6]["includes_labour"] = True                # the mixer hired with its operator
        lines[MASON]["for_lines"] = [1, 2, 3]
    f = with_rows(labour_row("labour_operator", 1, 30, 950, for_lines=[7]), edit=composite)
    assert issues(f)["labour_paid_twice"]["level"] == "fix"
    # with such a line on the form, each labour row says which lines it works on
    f = with_rows(labour_row("labour_operator", 1, 30, 950), edit=composite)
    assert "labour_lines_needed" in issues(f)
    # working on other lines is fine
    f = with_rows(labour_row("labour_operator", 1, 30, 950, for_lines=[1, 3]), edit=composite)
    assert validate(f, today=TODAY)["ready"]


def test_days_beyond_the_works_own_time_are_asked_to_confirm():
    f = with_rows(labour_row("labour_chowkidar", 2, 365, 450, activity="Guarding the material"))
    assert issues(f)["labour_days_beyond_work"]["level"] == "confirm"
    # within the six months (183 days) and its 10%: nothing
    f = with_rows(labour_row("labour_chowkidar", 2, 195, 450, activity="Guarding the material"))
    assert "labour_days_beyond_work" not in issues(f)


def test_how_many_workers_is_never_questioned_on_the_form():
    f = with_rows(labour_row("labour_operator", 40, 150, 950, activity="Running the machines"),
                  labour_row("labour_helper", 400, 150, 450, activity="Carrying and mixing"))
    assert validate(f, today=TODAY)["ready"]


def test_labour_among_the_estimate_lines_is_asked_to_move():
    f = with_rows({"group": "materials", "item": "Mason", "quantity": 50, "unit": "day",
                   "rate": 800, "basis": "market_rate"})
    assert issues(f)["labour_outside_section"]["level"] == "confirm"
    f = with_rows({"group": "machinery", "item": "JCB with operator", "quantity": 40,
                   "unit": "hour", "rate": 1200, "basis": "quotation"})
    assert "labour_outside_section" not in issues(f)
    assert "unit_for_material" not in issues(f)


def test_the_website_form_before_v11_needs_no_labour_table():
    f = road_form()
    f["form_version"] = "PSWIF v1.0"
    for ln in f["sites"][0]["lines"][BELDAR:MASON + 1]:
        for k in ("workers", "days", "activity", "for_lines", "material_id"):
            ln.pop(k, None)
    found = {i["code"] for i in validate(filed(f), today=TODAY)["issues"] if i["level"] == "fix"}
    assert not {c for c in found if c.startswith("labour") or c == "required"}, found


def test_junk_in_every_labour_field_never_breaks_the_form_or_the_agent():
    rng = random.Random(141)
    junk = [None, "", "x", -1, 0, 1e308, float("nan"), [], {}, [None], ["1"], True, "१२"]
    for _ in range(300):
        f = road_form()
        ln = f["sites"][0]["lines"][rng.choice([BELDAR, MASON])]
        for k in rng.sample(["workers", "days", "grade", "activity", "for_lines", "material_id",
                             "quantity", "rate", "unit", "includes_labour", "ref"], 4):
            ln[k] = rng.choice(junk)
        validate(f, today=TODAY)
        r = run(f)
        assert r.status in (Status.ASSESSED, Status.NOT_ASSESSABLE)


# ---- the agent: only blatant rates, and days beyond the work ----------------------------------

def test_honest_wages_are_never_asked():
    r = run(filed(road_form()))
    assert not codes(r) & {"LABOUR_RATE_FAR_ABOVE", "LABOUR_DAYS_BEYOND_WORK"}
    assert any("none is at twice it" in n for n in r.evidence["notes"])


def test_a_trade_at_twice_what_others_pay_it_is_asked():
    r = run(with_rows(edit=set_rate(MASON, 1700)))            # 2.1x the masons' Rs 800
    f = next(f for f in r.findings if f.code == "LABOUR_RATE_FAR_ABOVE")
    assert "mason at Rs 1,700 a day, 2.1 times Rs 800" in f.text
    assert f.evidence["rows"][0]["level"] == "trade"
    check_plain_language(f.text)


@pytest.mark.parametrize("rate", [1200, 1500, 1590])
def test_a_trade_paid_more_but_under_twice_is_not_a_question(rate):
    assert "LABOUR_RATE_FAR_ABOVE" not in codes(run(with_rows(edit=set_rate(MASON, rate))))


def test_a_few_days_at_a_high_rate_are_too_little_money_to_ask():
    f = with_rows(labour_row("labour_carpenter", 1, 4, 3000, activity="Fixing the door frame"))
    assert "LABOUR_RATE_FAR_ABOVE" not in codes(run(f))       # Rs 8,800 extra


def test_a_helper_called_highly_skilled_is_judged_as_a_helper():
    f = with_rows(labour_row("labour_helper", 6, 60, 1000, grade="highly_skilled",
                             activity="Carrying bricks and mortar"))
    r = run(f)
    asked = next(f for f in r.findings if f.code == "LABOUR_RATE_FAR_ABOVE")
    assert asked.evidence["rows"][0]["trade"] == "labour_helper"
    assert any("grade above the trade" in n for n in r.evidence["notes"])


def test_operators_are_paid_more_than_helpers_and_that_is_never_asked():
    f = with_rows(labour_row("labour_operator", 3, 90, 1100, activity="Running the mixer"),
                  labour_row("labour_helper", 30, 90, 500, activity="Feeding the mixer"))
    assert not codes(run(f)) & {"LABOUR_RATE_FAR_ABOVE"}


def test_a_trade_with_too_few_forms_falls_back_to_its_grades_pool_at_a_wider_margin():
    # no agency has filed welders; skilled trades (masons, carpenters) earn about Rs 800
    asked = run(with_rows(labour_row("labour_welder", 2, 40, 2100, activity="Welding the gate")))
    row = next(f for f in asked.findings if f.code == "LABOUR_RATE_FAR_ABOVE").evidence["rows"][0]
    assert row["level"] == "grade" and row["margin"] == labour.POOL_MARGIN
    calm = run(with_rows(labour_row("labour_welder", 2, 40, 1800, activity="Welding the gate")))
    assert "LABOUR_RATE_FAR_ABOVE" not in codes(calm)           # 2.25x: not blatant here


def test_a_trade_not_on_the_list_is_judged_at_its_declared_grades_pool():
    f = with_rows(labour_row("none", 2, 30, 2100, grade="skilled", activity="Stone carving work"))
    assert "LABOUR_RATE_FAR_ABOVE" in codes(run(f))


def test_the_pool_is_made_of_trades_never_of_declared_grades():
    idx = index()
    assert idx.by_key.get(("T|BETA", rates.pool_key("highly_skilled")))      # operators
    peers = {"labour_helper": PEERS["labour_helper"]}
    idx = index(peers)
    assert not idx.by_key.get(("T|BETA", rates.pool_key("highly_skilled")))
    assert len(idx.by_key[("T|BETA", rates.pool_key("unskilled"))]) == 6


def test_labour_moved_among_the_estimate_lines_is_still_judged_as_its_trade():
    f = with_rows({"group": "materials", "item": "Mason", "material_id": "labour_mason",
                   "quantity": 200, "unit": "day", "rate": 1800, "basis": "market_rate"})
    assert "LABOUR_RATE_FAR_ABOVE" in codes(run(f))


def test_workers_on_site_longer_than_the_work_lasts_are_asked():
    f = with_rows(labour_row("labour_chowkidar", 2, 365, 450, activity="Guarding the material"))
    key = next(i["key"] for i in validate(f, today=TODAY)["issues"]
               if i["code"] == "labour_days_beyond_work")
    f["confirmed"] = [key]
    found = next(x for x in run(f).findings if x.code == "LABOUR_DAYS_BEYOND_WORK")
    assert "confirmed the days" in found.text and found.evidence["rows"][0]["confirmed"]
    check_plain_language(found.text)


def test_a_labour_row_with_a_slip_is_not_assessed():
    f = with_rows(edit=lambda ln: ln[MASON].update(quantity=999))
    r = run(f)
    assert r.status == Status.NOT_ASSESSABLE and not r.findings


def test_a_rate_typo_is_held_until_answered_not_asked():
    f = with_rows(labour_row("labour_beldar", 10, 60, 45000, activity="Earthwork in the drain"))
    r = run(f)
    assert "LABOUR_RATE_FAR_ABOVE" not in codes(r)
    held = copy.deepcopy(f)
    held["confirmed"] = [i["key"] for i in validate(f, today=TODAY)["issues"]
                         if i["code"] == "rate_typo"]
    assert "LABOUR_RATE_FAR_ABOVE" in codes(run(held))


def test_a_labour_row_with_only_workers_and_days_is_priced_and_counted():
    # the website's labour schedule gives workers and days, not person-days (found by the
    # examples: such rows never reached the rate index or the whole estimate)
    f = road_form()
    for j in (BELDAR, MASON):
        del f["sites"][0]["lines"][j]["quantity"]
    f = filed(f)
    assert [x[2] for x in rates.confirmed_lines(f) if x[2].startswith("labour")] == [
        "labour_beldar", "labour_mason"]
    peers = []
    for a in range(6):
        g = copy.deepcopy(f)
        peers.append({"work_id": f"P{a}", "district_lgd": "T|BETA", "cost_form": g,
                      "cost_form_meta": {"saved_by": f"peer-{a}"}})
    idx = rates.RateIndex.build(peers)
    assert len(idx.by_key[("T|BETA", "labour_mason")]) == 6
    assert len(idx.by_key[("T|BETA", rates.pool_key("skilled"))]) == 6


def test_a_grade_nobody_here_files_is_judged_against_the_nearest_grade_with_room_per_step():
    # no operators or supervisors in the district: an "Other" highly skilled trade is compared
    # with the skilled pool (about Rs 800), with a quarter more room for the grade between
    peers = {k: v for k, v in PEERS.items() if k != "labour_operator"}
    f = with_rows(labour_row("none", 2, 30, 2600, grade="highly_skilled",
                             activity="Running the boring rig"))
    r = run(f, idx=index(peers))
    row = next(x for x in r.findings if x.code == "LABOUR_RATE_FAR_ABOVE").evidence["rows"][0]
    assert row["level"] == "other_grade" and row["pool"] == "skilled"
    assert row["margin"] == pytest.approx(labour.POOL_MARGIN * labour.GRADE_STEP)
    calm = with_rows(labour_row("none", 2, 30, 2400, grade="highly_skilled",
                                activity="Running the boring rig"))
    assert "LABOUR_RATE_FAR_ABOVE" not in codes(run(calm, idx=index(peers)))   # 3x: room


def test_a_trade_too_few_file_is_still_asked_two_grades_away_when_blatant():
    # only labourers have forms: masons are compared with them, with room for two grades
    peers = {"labour_beldar": PEERS["labour_beldar"]}
    honest = run(with_rows(), idx=index(peers))
    assert "LABOUR_RATE_FAR_ABOVE" not in codes(honest)            # masons at 1.8x labourers
    padded = run(with_rows(edit=set_rate(MASON, 1900)), idx=index(peers))
    row = next(f for f in padded.findings if f.code == "LABOUR_RATE_FAR_ABOVE").evidence["rows"][0]
    assert row["pool"] == "unskilled" and row["margin"] == pytest.approx(2.5 * 1.25 ** 2)
