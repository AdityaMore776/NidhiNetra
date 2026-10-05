"""T096: the digitised UP PWD rate book (reference/cost/sor_source, built by data/build_sor.py into
reference/cost/sor_candidates) reads through the engine's SoR functions, every number keeps its
source page, and nothing is switched on until the owner says so."""

import csv
import json
from pathlib import Path

import pytest

from drishti.agents.cost_estimate import rates

REF = Path(rates.__file__).resolve().parents[2] / "reference" / "cost"
BOOK = "up_pwd_jaunpur_ghazipur_2025-26"


@pytest.fixture(scope="module")
def rows():
    with (REF / "sor_source" / f"{BOOK}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def sor():
    return json.loads((REF / "sor_candidates" / f"{BOOK}.json").read_text(encoding="utf-8"))


def test_rates_read_through_the_engine(sor):
    assert rates.sor_rate(sor, "cement")[0] == 300.0          # 15.10.2025 revision, small work
    assert rates.sor_rate(sor, "brick")[0] == pytest.approx(6.9)   # Rs 6,900 per 1000
    assert rates.sor_rate(sor, "labour_unskilled")[0] == 423.0
    assert rates.sor_rate(sor, "labour_skilled")[0] == 521.0
    # steel went to "as per CPWD DSR"; quarry prices are not delivered prices; the local sand is
    # another grade than concrete's coarse sand: none of them is guessed
    for m in ("steel_rebar", "aggregate", "sand"):
        assert rates.sor_rate(sor, m) is None


def test_the_built_file_matches_the_table(rows, sor):
    mapped = {r["material_id"]: float(r["rate"]) for r in rows if r["material_id"]}
    assert {m: v["rate"] for m, v in sor["materials"].items()} == mapped
    assert len(sor["rows"]) == len(rows)


def test_every_number_has_its_page_and_basis(rows):
    for r in rows:
        assert r["pdf_page"].isdigit() and r["source"], r["row"]
        assert "gst_excluded" in r["basis"], r["row"]          # the whole book excludes GST


def test_superseded_and_quarry_rates_are_never_mapped(rows):
    for r in rows:
        if r["superseded_by"] or "at_quarry" in r["basis"]:
            assert not r["material_id"], r["row"]


def test_not_switched_on(sor):
    # the engine reads reference/cost/sor/<state>.json; a circle's book must not land there until
    # the engine takes an SoR per district, adds GST before comparing, and the owner agrees (T098)
    assert not (REF / "sor").exists() or not any((REF / "sor").glob("*.json"))
    assert rates.load_sor("Uttar Pradesh") is None
    assert sor["status"].startswith("candidate")
