import pytest

from drishti.validation.pii import mask


@pytest.mark.parametrize("text,gone,kept", [
    ("Cattle Shed near house of Sanjay Kumar Ward No 09 Panchayat Nallah", "Sanjay", "Ward No 09"),
    (r"SUBASH YADAV S\O NARAYAN YADAV K GHAR SOLAR LIGHT", "NARAYAN", "SOLAR LIGHT"),
    ("2 Solar Lights near the house of Smt. Krishna Devi, Ward 4", "Krishna", "Ward 4"),
    ("Solar pump at asinpara. contact Person Lalan Debsharma 9061234567", "9061234567", "asinpara"),
    ("Road from H/O Binod sarkar to school", "Binod", "to school"),
    ("Library near the house of Hazi Abdulla in Gram Panchayat Gardiya", "Abdulla", "Gardiya"),
    ("Payment to account 123456789012345", "123456789012345", "Payment"),
    ("CC Road from Ramesh Kale's house to Suresh Kale's house at Kaulkhed", "Kale", "Kaulkhed"),
    ("CC ROAD FROM RAMESH PATIL'S HOUSE TO SCHOOL", "RAMESH", "CC ROAD FROM"),
    ("Solar Light at Premises of Sheetla Mata Mandir at the request of Shri Anil Verma",
     "Anil", "Sheetla Mata Mandir"),
    ("Gram khairpur me mohan lal ke khet ke pas puliya nirman", "mohan", "Gram khairpur me"),
    ("balkaranpur mein Anil Kumar ke ghar ke pass solar light", "Anil", "balkaranpur mein"),
])
def test_personal_details_are_masked_places_are_kept(text, gone, kept):
    out = mask(text)
    assert gone not in out and kept in out


@pytest.mark.parametrize("text", ["Construction of Shri Ram Mandir road", "CC road in Shrirampur",
                                  "WS/MP807/2023-2024/32921", "Rs 5,00,000 for 300 m road",
                                  "Pera- St.John's Marthoma Church- Cheruvalloore Road",
                                  "Children's Park in Ward 4", "Women's hostel at Sitapur",
                                  "Panchayat bhawan ke pas CC road", "gram ke talab ka gahrikaran"])
def test_ordinary_text_is_untouched(text):
    assert mask(text) == text


@pytest.mark.parametrize("text,gone,kept", [
    # T056: a name before a home word with no possessive, read on the dashboard's descriptions
    ("PCC Road from Ramdev Bhagat house to Shyamlal Master house at ward no 15", "Ramdev",
     "at ward no 15"),
    ("PCC Road from Ramdev Bhagat house to Shyamlal Master house at ward no 15", "Shyamlal",
     "PCC Road from"),
    ("arvi chhoti mohan kale house to sudam pande house road construction", "sudam",
     "road construction"),
    ("Providing CC Drains from wine shop to Venkataramana land in SC Colony", "Venkataramana",
     "wine shop"),
    ("BALDEV YADAV K GHAR SE MANDIR TAK SOLAR LIGHT", "BALDEV", "SOLAR LIGHT"),
    ("gam thi Kanubhai Solanki na ghar sudhi CC road", "Kanubhai", "CC road"),
    ("Paver block from RAHIM’S HOUSE to masjid", "RAHIM", "to masjid"),
    # T092: the other spellings of a residence after the genitive, read on the dashboard
    ("Nahar pul se Arvind Maurya ka avas se pahle tak 200 mtr RCC road", "Arvind", "Nahar pul se"),
    ("chak se Ravi Kumar Verma ke awas tak 70 mtr interlocking", "Verma", "70 mtr"),
    ("Tigri men Manoj Dixit ke makaan se lekar Raju ke makaan ki or interlocking", "Raju",
     "se lekar"),
    ("Block Sasni mai Surendra Fauji kai Makaan sai Holi tak", "Surendra", "Block Sasni mai"),
    ("gam game Sanjaybhai Rathod na ghare thi mukhya rasta", "Sanjaybhai", "mukhya rasta"),
    ("Gudamb mein Manoj ke gher se Sunil Tyagi ke gher tak CC road", "Tyagi", "Gudamb mein"),
    ("kishanpura me Onkarlal ke niwas ke samne paver block", "Onkarlal", "kishanpura me"),
    ("Ahimanpur me Dinesh Mishra ki dukaan ke samne high mast", "Mishra", "Ahimanpur me"),
    ("Paver block from Army Barack to Kashyap Niwas Ward No. 04", "Kashyap", "Ward No. 04"),
    ("sim vistarna patel jitendrabhai kantibhai ghare thi mukhya rasta", "jitendrabhai",
     "mukhya rasta"),
])
def test_names_before_a_home_word_are_masked(text, gone, kept):
    out = mask(text)
    assert gone not in out and kept in out
    assert "[name] [name]" not in out and "]'[name]" not in out


@pytest.mark.parametrize("text", [
    "Construction of guest house at Sitapur", "Boundary wall of panchayat land",
    "Pump house and pipeline at Ward 7", "Barat ghar nirman gram Rampur", "Old age home building",
    "Ration shop building", "Construction of house for flood victims",
    "Fencing of government land near the school", "Community hall at Rampur",
    "Maruti row house compound wall", "Construction of WRC field channel",
    "PM Awas colony road", "Indira Awas ke pas CC road", "Meghwalon ki dhani me pipeline",
    "GOVT HSS NIWAS ME LAB SETUP"])
def test_ordinary_homes_and_lands_are_not_names(text):
    assert mask(text) == text


def test_a_name_masked_in_two_steps_reads_as_one():
    out = mask("ASHOK PATEL S\\O DINESH PATEL K GHAR SOLAR LIGHT")
    assert "DINESH" not in out and "[name] K GHAR" in out and "[name] [name]" not in out


@pytest.mark.parametrize("text,gone", [
    ("1- ASHOK PATEL S\\O DINESH PATEL K GHAR SOLAR LIGHT", "ASHOK"),
    ("Hand pump near Meena Devi W/o Ramesh Kumar house", "Meena"),
    ("Solar light at house of Gita Rani daughter of Hari Lal, ward 3", "Gita"),
])
def test_the_person_before_a_relation_marker_is_masked(text, gone):
    out = mask(text)
    assert gone not in out and ("S\\O" in out or "W/o" in out or "daughter of" in out)


def test_empty():
    assert mask(None) is None and mask("") == ""
