"""Duplicate Work v3 (T100): is this work already sanctioned at this site?

Questions only from the cost estimate form's map pins and the agency's own declarations; repeats
by words are notes (right about 2 times in 3, data/trial/simple_certain_trial.py)."""

import copy
import random
from datetime import date, timedelta

import pytest

from drishti.agents import registry
from drishti.agents.contract import Status
from drishti.agents.dup_split.agent import assess
from drishti.agents.dup_split.match import (
    misspelt_generic,
    place_agreement,
    place_words,
    sound_key,
    text_sim,
)
from drishti.agents.dup_split.repeat import PIN_METRES, RepeatIndex, metres, same_site

D = "639"
LAT, LON = 25.7500, 82.6900
DEG = 1 / 111_195            # one metre of latitude, in degrees


def _w(work_id, desc, amount=480_000.0, rec=date(2024, 1, 10), done=None, sanction=None,
       mp="MP A", wtype="COMMUNITY_HALL", status="SANCTIONED", district=D, form=None):
    w = {"work_id": work_id, "description": desc, "amount": amount, "recommended_date": rec,
         "completed_date": done, "sanction_date": sanction, "mp_name": mp,
         "work_type_code": wtype, "status": status, "district_lgd": district}
    if form is not None:
        w["cost_form"] = form
    return w


def _form(lat=LAT, lon=LON, wtype="COMMUNITY_HALL", nature="new", earlier=None, end=None,
          answers=None):
    loc = {"lat": lat, "lon": lon}
    if end:
        loc.update(end_lat=end[0], end_lon=end[1])
    work = {"work_type": wtype, "nature": nature}
    if earlier:
        work["earlier_work_id"] = earlier
    f = {"work": work, "sites": [{"location": loc}]}
    if answers:
        f["earlier_works"] = answers
    return f


def _filler(n=12):
    # ordinary works of the district, so its boilerplate rule has something to count
    return [_w(f"F{i}", f"Construction of drain at Gaonpur{i} ward", 900_000.0,
               rec=date(2023, 1, 1 + i), mp="MP Z", wtype="DRAIN") for i in range(n)]


HALL = "Construction of community hall near Shri Kalmeshwar Temple at Sirpur"


def asked(r):
    return [f.code for f in r.findings if f.risk > 0]


def notes(r):
    return [f.code for f in r.findings if f.risk == 0]


# ---- the question that needs no words: two map pins, one site ----------------------------------

@pytest.mark.parametrize("north,ask", [(0, True), (49, True), (51, False), (500, False)])
def test_a_sanctioned_work_within_50_m_of_the_pin_is_asked_about(north, ask):
    old = _w("OLD", "Community hall in the village", status="COMPLETED",
             rec=date(2023, 3, 1), done=date(2024, 2, 1), form=_form())
    new = _w("NEW", "Hall for the community, new building", rec=date(2025, 1, 5),
             status="RECOMMENDED", form=_form(lat=LAT + north * DEG))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert r.status == Status.ASSESSED
    assert (asked(r) == ["SANCTIONED_WORK_AT_THIS_SITE"]) is ask, (north, r.headline)
    if ask:
        assert "OLD" in r.headline and f"{north} m" in r.headline and r.risk == 0.7
        assert "completed on 2024-02-01" in r.headline


def test_the_50_m_line_is_measured_on_the_ground():
    assert abs(metres((LAT, LON), (LAT + 100 * DEG, LON)) - 100) < 0.5
    assert PIN_METRES == 50.0


def test_another_kind_of_asset_at_the_same_pin_is_two_works():
    old = _w("OLD", "Drain near the temple", wtype="DRAIN", status="COMPLETED",
             rec=date(2023, 3, 1), done=date(2024, 2, 1), form=_form(wtype="DRAIN"))
    new = _w("NEW", HALL, rec=date(2025, 1, 5), form=_form())
    assert not asked(assess(new, RepeatIndex.build(_filler() + [old, new])))


def test_only_a_sanctioned_and_earlier_work_counts_and_only_the_later_one_is_asked():
    rec_only = _w("REC", "Community hall", status="RECOMMENDED", rec=date(2023, 3, 1),
                  form=_form())
    new = _w("NEW", HALL, rec=date(2025, 1, 5), form=_form())
    idx = RepeatIndex.build(_filler() + [rec_only, new])
    assert not asked(assess(new, idx))                       # never sanctioned
    old = _w("OLD", "Community hall", status="SANCTIONED", rec=date(2023, 3, 1),
             sanction=date(2023, 6, 1), form=_form())
    idx = RepeatIndex.build(_filler() + [old, new])
    assert asked(assess(new, idx)) == ["SANCTIONED_WORK_AT_THIS_SITE"]
    assert "not yet completed" in assess(new, idx).headline
    assert not asked(assess(old, idx))                      # the first work is not the repeat


def test_a_road_is_one_site_only_when_both_ends_meet():
    a = ((LAT, LON), (LAT + 300 * DEG, LON))
    assert same_site(a, ((LAT + 10 * DEG, LON), (LAT + 290 * DEG, LON)), linear=True) is not None
    assert same_site(a, ((LAT + 300 * DEG, LON), (LAT, LON)), linear=True) is not None  # reversed
    # a road that starts where another ends is the next road, not the same one
    assert same_site(a, ((LAT + 300 * DEG, LON), (LAT + 600 * DEG, LON)), linear=True) is None
    assert same_site(((LAT, LON), None), ((LAT, LON), None), linear=True) is None    # no ends
    old = _w("OLD", "CC road", wtype="ROAD_CC", status="COMPLETED", rec=date(2023, 3, 1),
             done=date(2024, 2, 1), form=_form(wtype="ROAD_CC", end=a[1]))
    nxt = _w("NEXT", "CC road", wtype="ROAD_CC", rec=date(2025, 1, 5),
             form=_form(lat=a[1][0], wtype="ROAD_CC", end=(LAT + 600 * DEG, LON)))
    same = _w("SAME", "CC road", wtype="ROAD_CC", rec=date(2025, 1, 5),
              form=_form(lat=LAT + 5 * DEG, wtype="ROAD_CC", end=(a[1][0] + 5 * DEG, LON)))
    idx = RepeatIndex.build(_filler() + [old, nxt, same])
    assert not asked(assess(nxt, idx))
    assert asked(assess(same, idx)) == ["SANCTIONED_WORK_AT_THIS_SITE"]


# ---- continuations: what the agency declares is trusted, never asked ---------------------------

def _old_hall(done=date(2024, 2, 1)):
    return _w("OLD", HALL, status="COMPLETED", rec=date(2023, 3, 1), done=done, form=_form())


def test_a_declared_continuation_of_the_work_at_the_site_is_a_note():
    old = _old_hall()
    new = _w("NEW", HALL + " second phase", rec=date(2025, 1, 5),
             form=_form(nature="continuation", earlier="OLD"))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert not asked(r) and notes(r) == ["CONTINUES_SANCTIONED_WORK"] and r.risk == 0
    assert "continues work OLD" in r.headline and "completed on 2024-02-01" in r.headline


def test_the_agency_answering_continues_is_trusted():
    old = _old_hall()
    new = _w("NEW", "Hall extension", rec=date(2025, 1, 5),
             form=_form(answers=[{"earlier_work": "OLD", "answer": "continues"}]))
    assert not asked(assess(new, RepeatIndex.build(_filler() + [old, new])))


def test_saying_different_does_not_move_a_pin():
    old = _old_hall()
    new = _w("NEW", "Community building", rec=date(2025, 1, 5),
             form=_form(lat=LAT + 20 * DEG, answers=[{
                 "earlier_work": "OLD", "answer": "different",
                 "difference": "this one is behind the temple, the other in front"}]))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert asked(r) == ["SANCTIONED_WORK_AT_THIS_SITE"]
    assert "behind the temple" in r.headline and "a different work" in r.headline


@pytest.mark.parametrize("done,rebuilt", [(date(2024, 3, 1), True), (date(2021, 1, 1), False)])
def test_rebuilding_a_work_completed_under_three_years_ago_is_asked(done, rebuilt):
    old = _w("OLD", HALL, status="COMPLETED", rec=date(2020, 3, 1), done=done)
    new = _w("NEW", "Rebuilding of the hall", rec=date(2025, 1, 5),
             form=_form(nature="reconstruction", earlier="OLD"))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    if rebuilt:
        assert asked(r) == ["REBUILT_SOON_AFTER_COMPLETION"] and r.risk == 0.6
        assert "10 months" in r.headline and "OLD" in r.headline
    else:
        assert not asked(r) and notes(r) == ["CONTINUES_SANCTIONED_WORK"]


def test_a_declared_earlier_work_not_on_record_is_said():
    new = _w("NEW", HALL, rec=date(2025, 1, 5),
             form=_form(nature="extension", earlier="WS/MP1/2020-2021/1"))
    r = assess(new, RepeatIndex.build(_filler() + [new]))
    assert notes(r) == ["CONTINUES_SANCTIONED_WORK"] and "not on record" in r.headline
    assert r.risk == 0


# ---- words alone: a note for the officer, a question for the agency ----------------------------

def test_the_same_words_as_a_completed_work_are_a_note_never_counted():
    old = _w("OLD", HALL, status="COMPLETED", rec=date(2023, 3, 1), done=date(2024, 2, 1))
    new = _w("NEW", HALL.replace("Shri", "Sri"), rec=date(2025, 1, 5), mp="MP B",
             status="RECOMMENDED")
    idx = RepeatIndex.build(_filler() + [old, new])
    r = assess(new, idx)
    assert r.risk == 0 and not asked(r) and notes(r) == ["LOOKS_LIKE_SANCTIONED_WORK"]
    assert "OLD" in r.headline and "2 times in 3" in r.headline and "form asks" in r.headline
    assert [x.work_id for x in idx.candidates(new)] == ["OLD"]
    assert any("map pin" in x for x in r.limitations)


@pytest.mark.parametrize("a,b", [
    ("Construction of Boys Toilet (Ground Floor) in Muslim Higher Secondary School at Melapalayam",
     "Construction of Boys Toilet (First Floor) in Muslim Higher Secondary School at Melapalayam"),
    ("Construction of Reading room in SC Colony at Kondapur village",
     "Construction of Reading room in BC Colony at Kondapur village"),
    ("Construction of community hall north side of Sirpur chowk",
     "Construction of community hall south side of Sirpur chowk"),
    ("Construction of community hall for women at Sirpur chowk",
     "Construction of community hall for men at Sirpur chowk"),
    ("Construction of community hall in Ward No. 12 Sirpur", "Construction of community hall in "
     "Ward No. 13 Sirpur"),
    ("Construction of community hall at Sirpur chowk",
     "Construction of community hall at Sirpur chowk remaining work"),
    ("Construction of community hall at Sirpur chowk",
     "Construction of community hall at various villages Sirpur chowk"),
])
def test_two_works_the_words_tell_apart_are_not_look_alikes(a, b):
    old = _w("OLD", a, status="COMPLETED", rec=date(2023, 3, 1), done=date(2024, 2, 1))
    new = _w("NEW", b, rec=date(2025, 1, 5))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert not r.findings, (b, r.headline)


def test_a_description_naming_no_place_says_so():
    old = _w("OLD", "Construction of community hall", status="COMPLETED", rec=date(2023, 3, 1),
             done=date(2024, 2, 1))
    new = _w("NEW", "Construction of community hall", rec=date(2025, 1, 5))
    r = assess(new, RepeatIndex.build(_filler() + [old, new]))
    assert not r.findings and r.verdict == "NOT_SANCTIONED_BEFORE"
    assert any("names no place" in x for x in r.limitations)


def test_nothing_on_record_says_how_many_it_was_compared_with():
    r = assess(_w("NEW", HALL, rec=date(2025, 1, 5)), RepeatIndex.build(_filler(5)))
    assert r.verdict == "NOT_SANCTIONED_BEFORE" and "5 other works" in r.headline
    with_pin = _w("NEW", HALL, rec=date(2025, 1, 5), form=_form())
    r = assess(with_pin, RepeatIndex.build(_filler(5) + [with_pin]))
    assert "within 50 m of its map pin" in r.headline and r.confidence == 0.9


# ---- could not compare ------------------------------------------------------------------------

def test_without_an_index_or_a_date_it_says_it_could_not_compare():
    r = assess(_w("NEW", HALL), None)
    assert r.status == Status.NOT_ASSESSABLE and "not a clean chit" in r.headline
    idx = RepeatIndex.build(_filler(3))
    assert assess(_w("X", HALL, rec=None), idx).status == Status.NOT_ASSESSABLE
    assert assess(_w("X", "-"), idx).status == Status.NOT_ASSESSABLE
    # ... but a map pin is enough without words
    assert assess(_w("X", "-", form=_form()), idx).status == Status.ASSESSED


def test_registered_as_the_duplicate_slot_with_one_question():
    spec = registry.by_id()["dup_split"]
    assert spec.name == "Duplicate Work" and spec.weight == 0.20
    assert spec.question == "Is this work already sanctioned at this site?"


def test_damaged_forms_and_records_never_break_it():
    rng = random.Random(100)
    junk = [None, "", "x", -1, 0, 1e30, float("nan"), [], {}, True, "1,00,000", [1, 2]]
    old = _old_hall()
    base = _w("NEW", HALL, rec=date(2025, 1, 5),
              form=_form(nature="continuation", earlier="OLD",
                         answers=[{"earlier_work": "OLD", "answer": "different",
                                   "difference": "another site in the village"}]))
    for _ in range(300):
        w = copy.deepcopy(base)
        parts = [w, w["cost_form"], w["cost_form"]["work"],
                 w["cost_form"]["sites"][0]["location"], w["cost_form"]["earlier_works"][0]]
        for _ in range(rng.randint(1, 4)):
            part = rng.choice(parts)
            part[rng.choice(list(part) or ["x"])] = rng.choice(junk)
        try:
            r = assess(w, RepeatIndex.build(_filler(3) + [old, w]))
        except (TypeError, AttributeError, ValueError) as e:     # pragma: no cover
            pytest.fail(f"{type(e).__name__}: {e} on {w}")
        assert r.status in (Status.ASSESSED, Status.NOT_ASSESSABLE)


# ---- the word readers the look-alike note uses -------------------------------------------------

def test_a_typo_is_not_a_place_name():
    assert misspelt_generic("providign") and misspelt_generic("constrution")
    assert not misspelt_generic("sitapur")
    assert "providign" not in place_words("Providign of LED light with material at Sitapur")


def test_place_names_must_agree_word_by_word():
    assert place_agreement("podumbu sitapur", "podhumbu sitapur") >= 85
    assert place_agreement("annai therasa kovilpappakudi", "suriya kovilpappakudi") < 85


def test_one_village_spelt_two_ways_is_one_place():
    assert sound_key("chakwa") == sound_key("chakva")
    assert place_agreement("chakwa", "chakva") == 100.0
    assert place_agreement("sonpur", "sunpur") == 0.0


def test_hindi_and_english_wordings_of_one_work_read_alike():
    assert text_sim("Santpur Khurd me samudayik bhawan nirman",
                    "Santpur Khurd me community hall ka nirman karya") >= 0.9


def test_spec_sheets_and_ordinary_words_are_not_places():
    assert place_words("Highmast Solar Street light- Two Piece.") == ""
    assert place_words("High mast light ka adhisthapan prakhand ke antargat") == ""


# ---- one job cut into pieces just under a limit (the strictest form only) -----------------------

ROAD = "Construction of CC road from Sitapur chowk to Bhawanipur primary school"


@pytest.mark.parametrize("amounts,days,ask", [
    ((499_942, 499_981), 0, True),            # two pieces at 99.99%: asked
    ((482_000, 499_000, 499_500), 9, True),   # all at 96%+, within 30 days
    ((470_000, 499_000), 0, False),           # one piece at 94%: not the strictest form
    ((499_000, 499_000), 45, False),          # 45 days apart: not filed together
    ((499_000,) * 6, 0, False),               # six alike pieces: a series, not one job
])
def test_pieces_just_under_the_limit_are_asked_about(amounts, days, ask):
    first = date(2024, 12, 1)
    pieces = [_w(f"P{i}", f"{ROAD} reach-{i + 1}", a,
                 rec=first + timedelta(days=days if i else 0), wtype="ROAD_CC")
              for i, a in enumerate(amounts)]
    idx = RepeatIndex.build(_filler() + pieces)
    r = assess(pieces[0], idx)
    assert (asked(r) == ["SPLIT_JUST_UNDER_LIMIT"]) is ask, (amounts, days, r.headline)
    if ask:
        assert "just under the Rs 5.00 lakh limit" in r.headline and "Rs 4,99," in r.headline
        ev = r.findings[0].evidence
        assert ev["group_id"] == "G-P0" and ev["size"] == len(amounts)


def test_pieces_at_two_places_or_by_two_mps_are_two_jobs():
    a = _w("A", "Construction of CC road at Sitapur chowk", 499_000.0, rec=date(2024, 12, 1),
           wtype="ROAD_CC")
    b = _w("B", "Construction of CC road at Bhawanipur chowk", 499_000.0, rec=date(2024, 12, 1),
           wtype="ROAD_CC")
    c = _w("C", "Construction of CC road at Sitapur chowk", 499_000.0, rec=date(2024, 12, 1),
           wtype="ROAD_CC", mp="MP B")
    idx = RepeatIndex.build(_filler() + [a, b, c])
    assert not asked(assess(a, idx))


def test_a_new_recommendation_is_matched_with_its_pieces_on_the_spot():
    old = _w("OLD", f"{ROAD} reach-1", 499_500.0, rec=date(2024, 12, 1), wtype="ROAD_CC")
    idx = RepeatIndex.build(_filler() + [old])
    new = _w("NEW", f"{ROAD} reach-2", 499_800.0, rec=date(2024, 12, 3), wtype="ROAD_CC")
    r = assess(new, idx)
    assert asked(r) == ["SPLIT_JUST_UNDER_LIMIT"] and "OLD" in r.headline
