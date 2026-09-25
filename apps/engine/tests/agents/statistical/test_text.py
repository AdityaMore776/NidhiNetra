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
