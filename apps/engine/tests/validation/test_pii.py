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


def test_empty():
    assert mask(None) is None and mask("") == ""
