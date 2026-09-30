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
])
def test_personal_details_are_masked_places_are_kept(text, gone, kept):
    out = mask(text)
    assert gone not in out and kept in out


@pytest.mark.parametrize("text", ["Construction of Shri Ram Mandir road", "CC road in Shrirampur",
                                  "WS/MP807/2023-2024/32921", "Rs 5,00,000 for 300 m road"])
def test_ordinary_text_is_untouched(text):
    assert mask(text) == text


def test_empty():
    assert mask(None) is None and mask("") == ""
