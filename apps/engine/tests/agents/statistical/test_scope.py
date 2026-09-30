import pytest

from drishti.agents.statistical.scope import (
    GOODS,
    WORKS,
    many_sites,
    numbered_list,
    read,
    scope,
    stated_count,
    undescribed,
)


@pytest.mark.parametrize("text", ["Letter as per attached.", "List as per attached.", "NA", "n/a",
                                  "(no description)", "As per attechment", "", None,
                                  "Please see the attached list.", "???? ???? ?????",
                                  "MPLADS - 218"])
def test_undescribed(text):
    assert undescribed(text)


@pytest.mark.parametrize("text", ["solar light", "cc road", "Construction of community hall",
                                  "Purchase of books for school"])
def test_short_but_described(text):
    assert not undescribed(text)


@pytest.mark.parametrize("text", [
    "Solar light in allahabad loksabha chhetra",
    "Installation of CCTV Cameras at Various locations",
    "For supply of water pipeline and water pump in 50 different villages within Gambegre Block.",
    "Installation of street lights in ward nos 5,6,7,8,4,13",
    "works recomonded in letter no 216 for jamalpur block",
    "supply and installation of led light as pes enclosed list",
    "Books supply in 25 Govt. School of Khairagarh block",
])
def test_many_sites(text):
    assert many_sites(text)


@pytest.mark.parametrize("text", [
    "Loksabha kanpur ke antargat ward- 77 vishva bank barra B sector me tin shed ka nirman karya.",
    "Construction of Cattle Shed near house of Sanjay Kumar Ward No 09 Panchayat Nallah Block X",
    "Paver blocks at Bhimnagar Toramba block Lohara",
    "construction of road infront of bajrang bali mandir in tetulia 2 panchayat",
])
def test_one_site(text):
    assert not many_sites(text)


@pytest.mark.parametrize("text,expected", [
    ("Purchase Books for Library HS SADALPUR", GOODS),
    ("Supply of Dual Desk Benches to Government College", GOODS),
    ("Procurement of MRI Mechine to Hospital Agatti", GOODS),
    ("Construction of Library at Bothali", WORKS),
    ("C/o Ambulance road from main road to village", WORKS),
    ("CC Road Panchayat Bhavan se Public Water Supply tak", WORKS),
    ("Construction of Library and purchase of Books", WORKS),
])
def test_scope(text, expected):
    assert scope(text) == expected


@pytest.mark.parametrize("text,n", [
    ("Installation of 50 Nos of Street Lights at different places", 50),
    ("12 solar street lights", 12),
    ("Providing 30 Nos Bench and Desk to school", 30),
    ("PROVIDING ARM MODEL RCC SITTING BENCH AT DIFFERENT PLACES TOTAL 50 BENCH", 50),
    ("3 Laptop Computers for ALP School", 3),
])
def test_stated_count(text, n):
    assert stated_count(text) == n


@pytest.mark.parametrize("text", [
    "44-Installation of a high mast light near the intersection",
    "Installation of LED street light on 6 meter pole",
    "16 Meter High Mast with 8 LED Light at the main intersection",
    "6 X 200 WATT SEMI HIGH MAST LIGHT",
    "Construction of Anganwadi building Center no.33603120607 Division 35 Unit 9",
    "Year : 2022-23 SC Grant Solar street light work",
    "supply of 5 HP 8 Stage Pump set",
    "Installation of a light",
])
def test_not_a_count(text):
    assert stated_count(text) is None


def test_count_must_be_the_types_own_unit():
    text = "Pre fabricated bus shelter model 4 with 2 16 watt LED solar light"
    assert stated_count(text, "BUS_SHELTER") is None
    assert stated_count("Installation of 5 nos. solar lights in village", "STREET_LIGHT") == 5
    assert stated_count("Installation of 5 nos. solar lights in village", "ROAD_CC") is None


@pytest.mark.parametrize("text,bundle", [
    ("Installation of Mini Mast Light 35NOS", True),
    ("Supply and installation of 60 Highmast light in many areas", True),
    ("SUPPLY OF 4 NO 9 MTR OCTAGONAL HIGH MAST TOWER 6 x 150 WATT LED", True),
    ("install a high mast light of 12.5 mtr pole with 8 led each of 200 watt at kk college", False),
    ("6 X 200 WATT SEMI HIGH MAST LIGHT at the chauraha", False),
    ("Led Semi High Mast Light (10 LED) with 200-watt, 12.5 meter pole", False),
])
def test_high_masts_are_their_own_kind_and_lamps_are_not_masts(text, bundle):
    r = read("STREET_LIGHT", text)
    assert r.scope == "MAST" and r.bundle is bundle


@pytest.mark.parametrize("text", [
    "Semi High Mast Light at the following places- Gram Sabha Toliyani, Gram Sabha Dhaval",
    "Installation of High Mask Lights at 1 Dilawal Patti 2 Akhtiyarpur 3 Nakhatpur 4 Kodri",
    "60 Midil School, 32 High School & 16 College Me Pustak ki Aapurti",
])
def test_lists_of_places_are_many_sites(text):
    assert many_sites(text)


def test_numbered_list_needs_one_two_three():
    assert numbered_list("at 1 Dilawal 2 Akhtiyarpur 3 Nakhatpur")
    assert not numbered_list("Construction of 3 rooms in school no 2 ward 1")


def test_count_after_the_item():
    assert stated_count("Street Light 35NOS") == 35
    assert stated_count("Solar light - 16 nos") == 16


def test_a_clean_reading_is_one_described_job_at_one_site():
    assert read("ROAD_CC", "Construction of CC road in village X").clean
    assert not read("ROAD_CC", "Letter as per attached").clean
    assert not read("STREET_LIGHT", "Installation of 12 solar street lights").clean
