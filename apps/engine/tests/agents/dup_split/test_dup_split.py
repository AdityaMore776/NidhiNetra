"""Duplicate & Split v2 (T051): the rules run on any work, seen before or not."""

from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.dup_split.agent import assess, group_risk, pair_risk
from drishti.agents.dup_split.match import (
    DupIndex,
    misspelt_generic,
    place_agreement,
    place_words,
    sides,
    text_sim,
)

D = "639"


def _w(work_id, desc, amount=480_000.0, rec=date(2024, 1, 10), done=None, mp="MP A",
       wtype="ROAD_CC", status="SANCTIONED", district=D):
    return {"work_id": work_id, "description": desc, "amount": amount, "recommended_date": rec,
            "completed_date": done, "mp_name": mp, "work_type_code": wtype, "status": status,
            "district_lgd": district}


def _filler(n=12):
    # ordinary works of the district, so its boilerplate rule has something to count
    return [_w(f"F{i}", f"Construction of community hall at Gaonpur{i} ward", 900_000.0,
               rec=date(2023, 1, 1 + i), mp="MP Z", wtype="COMMUNITY_HALL") for i in range(n)]


ROAD = "Construction of CC road from Sitapur chowk to Bhawanipur primary school"


def test_a_copy_of_a_completed_work_filed_under_a_new_id_is_found():
    # the owner's scenario: v1 said "compared, no repeat found" without comparing anything
    old = _w("OLD", ROAD, rec=date(2023, 6, 1), done=date(2024, 2, 1), status="COMPLETED")
    idx = DupIndex.build(_filler() + [old])
    new = _w("NEW-1", ROAD, rec=date(2024, 9, 1), mp="MP B", status="RECOMMENDED")
    r = assess(new, idx)
    assert r.status == Status.ASSESSED and r.verdict == "FUNDED_AGAIN_AFTER_COMPLETION"
    assert "OLD" in r.headline and "already been completed" in r.headline
    assert 0.55 <= r.risk <= 0.95


def test_a_new_work_with_no_match_says_how_many_it_was_compared_with():
    idx = DupIndex.build(_filler(5))
    r = assess(_w("NEW-2", ROAD, rec=date(2024, 9, 1)), idx)
    assert r.verdict == "NO_REPEAT_FOUND" and "5 other works" in r.headline


def test_a_description_naming_no_place_never_reads_as_no_repeat_found():
    # 19% of real works name no place; a repeat of them can be neither confirmed nor ruled out
    idx = DupIndex.build(_filler(5))
    r = assess(_w("NEW-9", "Construction of community hall", rec=date(2024, 9, 1)), idx)
    assert r.verdict == "NO_SITE_NAMED" and r.risk == 0
    assert "cannot be ruled out" in r.headline and "no repeat" not in r.headline.lower()


def test_without_an_index_it_says_it_could_not_compare():
    r = assess(_w("NEW-3", ROAD), None)
    assert r.status == Status.NOT_ASSESSABLE and "not a clean chit" in r.headline
    idx = DupIndex.build(_filler(3))
    for bad in ({"description": "-"}, {"recommended_date": None}, {"amount": 0}):
        assert assess(_w("X", ROAD) | bad, idx).status == Status.NOT_ASSESSABLE


def test_different_villages_sharing_district_boilerplate_are_not_a_pair():
    # 38 of the first 40 v2 pairs read by eye were like this (DEV1)
    base = [_w(f"B{i}", f"High mast light recommended by implemneting agency pccd bijnore "
               f"village Gaonpur{i}", 170_000.0, rec=date(2023, 1, 1 + i)) for i in range(20)]
    a = _w("A", "High mast light recommended by implemneting agency pccd bijnore village Mandori",
           170_000.0, rec=date(2024, 1, 1), done=date(2024, 3, 1), status="COMPLETED")
    b = _w("B", "High mast light recommended by implemneting agency pccd bijnore village Paniyala",
           170_000.0, rec=date(2024, 9, 1), mp="MP B")
    idx = DupIndex.build(base + [a, b])
    assert assess(b, idx).verdict == "NO_REPEAT_FOUND"


def test_opposite_sides_of_one_road_are_two_works():
    a = _w("A", "Bituminous road at Fifth Street North side in Maharaja Nagar Viraganur",
           rec=date(2024, 1, 1), done=date(2024, 3, 1), status="COMPLETED")
    b = _w("B", "Bituminous road at Fifth Street South side in Maharaja Nagar Viraganur",
           rec=date(2024, 9, 1), mp="MP B")
    assert sides(a["description"]) != sides(b["description"])
    assert assess(b, DupIndex.build(_filler() + [a, b])).verdict == "NO_REPEAT_FOUND"


def test_one_job_cut_into_pieces_the_same_day_under_the_limit():
    pieces = [_w(f"P{i}", "CC road at Sapti village from temple to school", 496_000.0,
                 rec=date(2024, 3, 5)) for i in range(3)]
    idx = DupIndex.build(_filler() + pieces)
    r = assess(pieces[0], idx)
    assert r.verdict == "SPLIT_AT_ONE_SITE"
    assert "on the same day" in r.headline and "just under Rs 5.00 lakh" in r.headline
    assert "sapti" not in r.headline.lower()          # place words stay in the evidence
    assert r.evidence["group_id"] and r.findings[0].evidence["under_limit"]


def test_pieces_naming_different_people_are_an_ordinary_batch():
    # TEST groups: "near X's house" / "near Y's house" were different spots, not a split
    pieces = [_w(f"P{i}", f"Solar light at public place near house of {n} in Kosada village",
                 18_644.0, rec=date(2024, 3, 5)) for i, n in enumerate(("Ganga Lodhi",
                                                                        "Ram Kishan Yadav"))]
    idx = DupIndex.build(_filler() + pieces)
    assert assess(pieces[0], idx).verdict == "NO_REPEAT_FOUND"


def test_a_typo_is_not_a_place_name():
    assert misspelt_generic("providign") and misspelt_generic("constrution")
    assert not misspelt_generic("sitapur")
    assert "providign" not in place_words("Providign of LED light with material at Sitapur")


def test_place_names_must_agree_word_by_word():
    assert place_agreement("podumbu sitapur", "podhumbu sitapur") >= 85
    assert place_agreement("annai therasa kovilpappakudi", "suriya kovilpappakudi") < 85


def test_hindi_and_english_wording_of_one_work_read_alike():
    assert text_sim("CC sadak nirman Sitapur", "CC road construction Sitapur") > 0.9


def test_signals_grow_with_the_evidence():
    # v1 gave six fixed values; 16,372 works shared 0.15
    assert pair_risk("after_completed", 0.75) == pytest.approx(0.55)
    assert pair_risk("after_completed", 1.0) == pytest.approx(0.95)
    assert pair_risk("while_open", 0.8) < pair_risk("while_open", 0.95)
    small = group_risk({"kind": "bulk_order", "size": 3, "total": 300_000})
    big = group_risk({"kind": "bulk_order", "size": 9, "total": 900_000})
    assert small < big <= 0.20
    loose = group_risk({"kind": "same_site_split", "size": 3, "total": 3 * 410_000,
                        "under_limit": True, "limit": 500_000})
    tight = group_risk({"kind": "same_site_split", "size": 3, "total": 3 * 499_000,
                        "under_limit": True, "limit": 500_000})
    assert loose < tight


def test_a_large_same_place_group_is_read_as_a_series():
    pieces = [_w(f"P{i}", "Water tenker supply at Publiic place Jhabua", 160_000.0,
                 rec=date(2024, 3, 5), wtype="WATER_TANK") for i in range(7)]
    r = assess(pieces[0], DupIndex.build(_filler() + pieces))
    assert r.verdict == "BULK_ORDER" and r.risk <= 0.20


# ---- 2 Oct 2026: stretches, repairs, sound-alike places, works seen only as completed ---------

def test_numbered_pieces_of_one_road_are_a_split_into_stretches():
    from drishti.agents.dup_split.match import segment, site_numbers

    assert segment("CC road at Sitapur part-2") == "part:2"
    assert segment("CC road Sitapur Part II") == "part:2"
    assert segment("Laying of CC Road from Hanuman Temple to GP Building Bit-III") == "bit:3"
    assert segment("CC road at Sitapur chainage 250 to 500 m") == "ch:250-500"
    assert site_numbers("CC road ward no 12 part-2") == "12"     # the piece is not the site
    pieces = [_w(f"P{i}", f"Construction of CC road from Sitapur chowk to Bhawanipur school "
                          f"part-{i + 1}", amount=495_000.0, rec=date(2024, 3, 1))
              for i in range(3)]
    idx = DupIndex.build(_filler() + pieces)
    r = assess(pieces[0], idx)
    assert r.verdict == "SPLIT_INTO_STRETCHES" and "part:1, part:2, part:3" in r.headline
    assert "just under Rs 5.00 lakh" in r.headline and r.risk >= 0.6
    # numbered pieces are never reported as repeats of one another
    assert not any(f.code in ("REPEATED_WHILE_OPEN", "FUNDED_AGAIN_AFTER_COMPLETION")
                   for f in r.findings)


def test_a_repair_soon_after_the_work_was_built_is_asked_about():
    built = _w("BUILT", "Construction of community hall at Sitapur near primary school",
               amount=900_000.0, rec=date(2023, 6, 1), done=date(2024, 1, 10),
               status="COMPLETED", wtype="COMMUNITY_HALL")
    repair = _w("FIX", "Repair of community hall at Sitapur near primary school",
                amount=300_000.0, rec=date(2024, 6, 1), mp="MP B", wtype="COMMUNITY_HALL")
    elsewhere = _w("FIX2", "Repair of community hall at Bhawanipur near panchayat bhawan",
                   amount=300_000.0, rec=date(2024, 6, 1), mp="MP B", wtype="COMMUNITY_HALL")
    idx = DupIndex.build(_filler() + [built, repair, elsewhere])
    r = assess(repair, idx)
    assert r.verdict == "REPAIR_SOON_AFTER_BUILT" and "BUILT" in r.headline
    assert "143 days after that work was completed" in r.headline
    assert assess(elsewhere, idx).verdict != "REPAIR_SOON_AFTER_BUILT"
    # years later a repair is ordinary upkeep
    late = _w("FIX3", repair["description"], amount=300_000.0, rec=date(2027, 6, 1), mp="MP B",
              wtype="COMMUNITY_HALL")
    assert assess(late, DupIndex.build(_filler() + [built, late])).risk == 0


def test_one_village_spelt_two_ways_is_one_place():
    from drishti.agents.dup_split.match import sound_key

    assert sound_key("chakwa") == sound_key("chakva")
    assert sound_key("ghurpur") == sound_key("gurpur")
    assert place_agreement("chakwa", "chakva") == 100.0
    assert place_agreement("sonpur", "sunpur") == 0.0


def test_hindi_and_english_wordings_of_one_work_read_alike():
    assert text_sim("Santpur Khurd me samudayik bhawan nirman",
                    "Santpur Khurd me community hall ka nirman karya") >= 0.9


def test_spec_sheets_and_ordinary_words_are_not_places():
    spec = ("Installation of Solar LED Light with Pole (Lights 24Watt x 2, Pole 7mtr. Octagonal "
            "with Manual Ladder, Battery 12.8V,30A H Lithium ferro, Module 150Wp")
    assert place_words(spec) == ""
    assert place_words("Highmast Solar Street light- Two Piece.") == ""
    assert place_words("High mast light ka adhisthapan prakhand ke antargat") == ""


def test_a_work_seen_only_as_completed_can_be_the_first_of_a_repeat():
    # the dashboard's Completed table carries no recommendation date
    old = _w("OLD-C", ROAD, rec=None, done=date(2024, 2, 1), status="COMPLETED")
    idx = DupIndex.build(_filler() + [old])
    r = assess(_w("NEW-C", ROAD, rec=date(2024, 9, 1), mp="MP B", status="RECOMMENDED"), idx)
    assert r.verdict == "FUNDED_AGAIN_AFTER_COMPLETION" and "OLD-C" in r.headline
    # ... and is compared itself, though it can never be the later of two
    assert assess(old, idx).status == Status.ASSESSED


# ---- read by eye on the dashboard's split flags (2 Oct 2026, T056)

@pytest.mark.parametrize("a,b", [
    ("Construction of Resting Barracks with attached wash rooms for Men in the District Police "
     "Office, Eluru", "Construction of Resting Barracks with attached wash rooms for Women in the "
     "District Police Office, Eluru"),
    ("Construction of new building Vishranthi Dhamam (Male block) at Govt General Hospital",
     "Construction of new building Vishranthi Dhamam (Female block) at Govt General Hospital"),
    ("Boys toilet at Govt High School Kalathurpatti",
     "Girls toilet at Govt High School Kalathurpatti"),
])
def test_a_mens_and_a_womens_building_are_two_works(a, b):
    x = _w("M1", a, 3_198_000.0, rec=date(2024, 10, 25), wtype="OTHER")
    y = _w("W1", b, 3_199_000.0, rec=date(2024, 10, 25), wtype="OTHER")
    idx = DupIndex.build(_filler() + [x, y])
    for w in (x, y):
        r = assess(w, idx)
        assert not [f for f in r.findings if f.risk > 0], (w["work_id"], r.verdict)


def test_two_girls_toilets_are_still_compared_as_alike():
    # the same gender on both is no difference at all
    pieces = [_w(f"G{i}", "Girls toilet at Govt High School Kalathurpatti", 496_000.0,
                 rec=date(2024, 3, 5), wtype="TOILET_BLOCK") for i in range(2)]
    r = assess(pieces[0], DupIndex.build(_filler() + pieces))
    assert r.verdict == "SPLIT_AT_ONE_SITE" and r.risk > 0


def test_alike_works_whose_total_crosses_no_limit_are_said_not_asked():
    # two Rs 34,000 street lights near one place: 0 of 5 such groups read as a real split
    lights = [_w(f"L{i}", "Installation of 1 no solar street light near Bamangachi Roy Para",
                 34_259.0, rec=date(2024, 11, 27), wtype="STREET_LIGHT") for i in range(2)]
    r = assess(lights[0], DupIndex.build(_filler() + lights))
    assert not [f for f in r.findings if f.risk > 0]
    below = [f for f in r.findings if f.code == "ALIKE_BELOW_LIMIT"]
    assert below and "Rs 5.00 lakh" in below[0].text and r.risk == 0
