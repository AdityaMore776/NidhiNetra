"""T061: a work's place from its description, matched to India Post offices of its own district."""

from drishti.planner import locate as loc

# name, lat, lon, shared (1 = a position 3+ offices carry: an area, not a village)
OFFICES = [
    ["bijdih", 22.50, 72.90, 0],
    ["vasad", 22.45, 73.07, 0],
    ["rachandarthirumalai", 10.76, 78.54, 0],
    ["sapti", 22.60, 72.95, 0],
    ["walki", 22.70, 72.80, 0],
    ["kothimir", 22.55, 72.85, 1],
    ["rampur", 22.40, 72.90, 0],         # also a generic word: never matched
    ["dupli", 22.40, 72.90, 0],          # one name, two offices 30 km apart: ambiguous
    ["dupli", 22.67, 72.90, 0],
    ["twin", 22.40, 72.90, 0],           # one name, two offices 1 km apart: one place
    ["twin", 22.409, 72.90, 0],
    ["anand", 22.55, 72.95, 0],          # the district's own name: boilerplate, not a place
]
GENERIC = frozenset({"rampur", "road", "village"})


def m(desc: str) -> loc.Match | None:
    return loc.match(desc, loc.index(OFFICES), district_name="Anand", generic=GENERIC)


def test_a_named_village_is_found_with_its_position():
    got = m("CC road in village Bijdih")
    assert got is not None
    assert (got.place, got.lat, got.lon, got.precision) == ("bijdih", 22.50, 72.90, "village")


def test_a_name_written_as_two_words_matches_the_one_word_office():
    got = m("Construction of Two Class Room Building on GHSS Rachandar Thirumalai Village")
    assert got is not None and got.place == "rachandarthirumalai"


def test_matching_ignores_case_punctuation_and_needs_whole_words():
    assert m("CC ROAD, VASAD-GAM") is not None
    assert m("CC road at Vasadpura") is None           # Vasad inside a longer word is not Vasad


def test_the_place_after_a_cue_word_wins_over_another_name():
    got = m("Hall for Walki people built at Sapti")
    assert got is not None and got.place == "sapti"
    got = m("Road from Sapti to village Walki")
    assert got is not None and got.place == "walki"


def test_a_name_beside_a_block_word_is_a_block_and_loses_to_a_village():
    got = m("Community hall at Sapti (M)")
    assert got is not None and (got.place, got.precision) == ("sapti", "block")
    got = m("Road for Walki village, Taluk Sapti")
    assert got is not None and (got.place, got.precision) == ("walki", "village")
    got = m("Drain in Walki (V) of Sapti (M)")
    assert got is not None and got.place == "walki"


def test_short_block_words_come_before_the_block_so_the_name_before_them_is_a_village():
    # T062 eye sample: "Nesari, Tal.Gadhinglaj" and "At. Ashti Tq. Hadgaon" name the village
    got = m("Sabhagruh, Highschool, Sapti, Tal. Walki")
    assert got is not None and (got.place, got.precision) == ("sapti", "village")
    got = m("CC road At. Sapti Tq. Walki")
    assert got is not None and (got.place, got.precision) == ("sapti", "village")
    got = m("Solar light, Taluka. Sapti")
    assert got is not None and (got.place, got.precision) == ("sapti", "block")


def test_a_name_beside_a_district_word_is_the_district_not_a_place():
    # T062 eye sample: "...Butchireddypalem of Nellore District" in Sri Potti Sriramulu Nellore
    assert m("CC road near the apartment of Vasad District") is None
    assert m("Smart class, Dist. Vasad") is None
    assert m("CC road, Sapti (M), Vasad (D)").place == "sapti"


def test_without_a_cue_the_first_named_place_wins():
    got = m("Sapti Walki link road")
    assert got is not None and got.place == "sapti"


def test_a_shared_position_is_an_area_not_a_village():
    got = m("Hand pump at Kothimir")
    assert got is not None and got.precision == "area"


def test_generic_words_the_district_name_and_ambiguous_names_never_match():
    assert m("CC road at Rampur") is None
    assert m("Community hall at Anand") is None
    assert m("Hall at Dupli") is None
    got = m("Hall at Twin")
    assert got is not None and got.place == "twin"


def test_nothing_to_read_gives_no_match():
    assert m("") is None
    assert m(None) is None
    assert m("Letter as per attached") is None


def test_locate_falls_back_to_the_district_start_and_says_so():
    real = loc.locate("613", "Construction of Two Class Room Building on GHSS Rachandar "
                             "Thirumalai Village at Thokaimalai Panchayat.")
    assert real is not None and real.precision == "village"
    assert real.place == "rachandarthirumalai"
    rough = loc.locate("613", "Letter as per attached")
    assert rough is not None and rough.precision == "district" and rough.place is None
    start = loc.district_start("613")
    assert (rough.lat, rough.lon) == (start.lat, start.lon)


def test_an_unknown_district_cannot_be_located():
    assert loc.locate("no-such-district", "CC road in village Bijdih") is None
    assert loc.locate(None, "CC road in village Bijdih") is None
    assert loc.district_start("no-such-district") is None


def test_an_office_from_another_district_is_never_used():
    # Bijdih is not a Karur office: a Karur work naming it stays at the district start
    got = loc.locate("613", "CC road in village Bijdih")
    assert got is not None and got.precision == "district"
