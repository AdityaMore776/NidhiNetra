import math

import pytest

from drishti.agents.statistical.text import reads_as_bundle, stated_length


@pytest.mark.parametrize("text", [
    "Installation of 60 Highmast lights",
    "Supply and installation of 981 solar street lights",
    "Solar lights at different places in the block",
    "Installation of street light as per attached list",
    "Supply of two hundred LED bulbs",
])
def test_bulk_orders_read_as_bundles(text):
    assert reads_as_bundle(text)


@pytest.mark.parametrize("text", [
    "Construction of CC road in village Bijdih",
    "Construction of 1 community hall at Nadauli",
    "",
    None,
])
def test_single_works_do_not(text):
    assert not reads_as_bundle(text)


def test_stated_length_reads_metres():
    assert stated_length("CC road 450 mtr from school to temple") == 450.0
    assert stated_length("Construction of road 1,200 metres") == 1200.0


def test_stated_length_refuses_widths_and_typos():
    assert math.isnan(stated_length("road 5 mt width"))
    assert math.isnan(stated_length("road 20,000 mtr"))
    assert math.isnan(stated_length("no length here"))


@pytest.mark.parametrize("text", [
    "SUPPLY AND INSTALLATION OF LED SEMI HIGH MASK LIGHT AT 217 DIFFRENT PLACES IN DISTRICT",
    "installation of semi high mast light in maximum 810 location of different gram panchayat",
    "supply and installation of led semi high mast light as per list enclosed",
    "PER LIGHT COST 283000 AND 60 DIFFERENT PLACE OF COST 16980000.00 (AS PER LIST)",
])
def test_real_bulk_orders_the_first_regex_missed(text):
    # read off the top of the 2026-09-25 dry run over the real corpus
    assert reads_as_bundle(text)


def test_kilometres_are_read_only_when_asked():
    assert math.isnan(stated_length("Laying of 1.2 Km Black Top Road in Gangaram Village"))
    assert stated_length("Laying of 1.2 Km Black Top Road", allow_km=True) == pytest.approx(1200.0)
    assert stated_length("CC road 450 mtr", allow_km=True) == 450.0
    # 25 km is a corridor, not one village road
    assert math.isnan(stated_length("road of 25 km", allow_km=True))
