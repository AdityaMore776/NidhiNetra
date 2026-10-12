"""Site Progress v2 (T510): the record's own words against what the work's photos show.

The photo readers (a local zero-shot model, the plaque's text, an optional vision-language
model) run offline and store readings; these tests drive the engine's rules with stored
readings, so they need no model.
"""

import json
from datetime import date

import pytest

from drishti.agents.contract import Status
from drishti.agents.photo_evidence.index import PhotoIndex
from drishti.agents.site_progress import claims, observe, plaque
from drishti.agents.site_progress import photos as agent
from drishti.agents.site_progress.readers import GeminiReader, QuotaReached

AS_OF = date(2026, 9, 26)


def reading(group: str, built: float, not_built: float, not_site: float = 0.0) -> dict:
    """A photo's stored zero-shot reading, for one concept group."""
    return {"reader": "test", "version": observe.VERSION,
            "groups": {group: {"built": built, "not_built": not_built, "not_site": not_site}}}


def photo(i: int, site: dict | None = None, stamps=None, sha: str | None = None) -> dict:
    f = {"id": f"P{i}", "ext": "jpg", "sha256": sha or f"sha{i}", "stamps": stamps or []}
    if site is not None:
        f["site"] = site
    return f


def work(files, status="COMPLETED", wtype="COMMUNITY_HALL",
         desc="Construction of community hall at Rampur ward 4", **kw) -> dict:
    return {"work_id": "W1", "work_type_code": wtype, "description": desc, "status": status,
            "recommended_date": date(2024, 1, 10), "completed_date": date(2024, 6, 1),
            "district_lgd": "", "amount": 900000, "evidence": {"files": files}, **kw}


EMPTY_PLOT = reading("building", built=0.05, not_built=0.90)
HALL = reading("building", built=0.80, not_built=0.10)


def codes(r) -> set[str]:
    return {f.code for f in r.findings if f.risk > 0}


# ----------------------------------------------------------------- the stored reading

def test_scores_become_one_reading_per_group_that_sums_to_one():
    logits = {p.text: 0.0 for p in observe.prompts()}
    road = next(p.text for p in observe.prompts() if p.group == "road_cc" and p.kind == "built")
    logits[road] = 5.0
    obs = observe.observation(logits, reader="test")
    g = obs["groups"]["road_cc"]
    assert g["built"] > 0.5 and abs(g["built"] + g["not_built"] + g["not_site"] - 1) < 1e-6
    assert obs["groups"]["lights"]["not_built"] == 0.0        # a group that cannot say "absent"
    assert set(obs["groups"]) == set(observe.groups())


@pytest.mark.parametrize("built,not_built,not_site,expected", [
    (0.80, 0.10, 0.10, "shows"), (0.05, 0.90, 0.05, "not_built"), (0.10, 0.10, 0.80, "not_site"),
    (0.30, 0.50, 0.20, "unclear"), (0.20, 0.75, 0.05, "unclear")])
def test_one_photo_reads_shows_not_built_not_a_site_or_unclear(built, not_built, not_site,
                                                               expected):
    assert observe.read(reading("building", built, not_built, not_site), "building") == expected


def test_a_photo_with_no_reading_is_not_read():
    assert observe.read(None, "building") is None
    assert observe.read({"version": "old", "groups": {}}, "building") is None


# ----------------------------------------------------------------- claims: the record's words

def test_a_completed_work_claims_its_asset_in_its_own_words():
    cs = claims.claims_of(work([]))
    asset = [c for c in cs if c.kind == "asset"]
    assert len(asset) == 1 and asset[0].group == "building"
    assert "community hall at Rampur" in asset[0].text and asset[0].source == "record"


def test_an_open_work_claims_nothing_built_and_an_unknown_type_cannot_be_pictured():
    assert not [c for c in claims.claims_of(work([], status="SANCTIONED")) if c.kind == "asset"]
    assert not [c for c in claims.claims_of(work([], wtype="OTHER")) if c.kind == "asset"]


def test_counts_lengths_and_the_officers_notes_are_claims_too():
    w = work([], wtype="ROAD_CC", desc="CC road 300 mtr from school to temple",
             field_notes=["Roof slab cast", "  "])
    kinds = {c.kind: c for c in claims.claims_of(w)}
    assert kinds["length"].text.startswith("300 m")
    assert kinds["field"].text == "Roof slab cast" and kinds["field"].source == "field notes"


# ----------------------------------------------------------------- plaque text

def test_an_mplads_plaque_is_read_with_its_dates_and_nothing_personal():
    text = ("MPLADS 2023-24 Construction of Boundary Wall at Shamshan Ghat Estimated Cost Rs "
            "4,95,000 Date of Start: 01/10/2023 Date of Completion: 31/12/2023 Sh. Some Name MP")
    p = plaque.read(text)
    assert p["scheme"] is True
    assert {"label": "start", "date": "2023-10-01"} in p["dates"]
    assert {"label": "completion", "date": "2023-12-31"} in p["dates"]
    assert "Name" not in json.dumps(p)                        # facts only, never the text


@pytest.mark.parametrize("text", [
    "Lat 24.88 Long 74.62 12/02/2024 10:31 AM GPS Map Camera",   # a GPS stamp, not a plaque
    "Gram Panchayat Rampur Welcome", ""])
def test_text_that_is_not_an_mplads_plaque_is_not_one(text):
    assert plaque.read(text)["scheme"] is False


def test_ocr_that_glues_words_together_still_reads():
    """RapidOCR's own output for a drawn plaque (2 Oct 2026 smoke test): spaces dropped."""
    lines = ["MPLADS2023-24", "CONSTRUCTIONOF BOUNDARYWALL", "ATSHAMSHANGHAT",
             "DATEOFSTART:01/10/2023", "DATEOFCOMPLETION:31/12/2023"]
    p = plaque.read(" ".join(lines))
    assert p["scheme"] is True
    assert p["dates"] == [{"label": "start", "date": "2023-10-01"},
                          {"label": "completion", "date": "2023-12-31"}]
    assert plaque.read("SANSADNIDHI SE")["scheme"] is True


def test_romanised_scheme_names_count():
    assert plaque.read("SANSAD NIDHI SE NIRMIT")["scheme"] is True
    assert plaque.read("M.P. LAD SCHEME 2024")["scheme"] is True


# ----------------------------------------------------------------- the engine's answers

def test_no_photo_is_not_applicable_and_never_a_clean_chit():
    r = agent.assess(work([]), AS_OF)
    assert r.status == Status.NOT_APPLICABLE and "not a clean chit" in r.headline


def test_photos_never_read_cannot_be_assessed():
    r = agent.assess(work([photo(1), photo(2)]), AS_OF)
    assert r.status == Status.NOT_ASSESSABLE and r.risk == 0


def test_completed_but_every_photo_shows_an_empty_plot_needs_a_site_check():
    r = agent.assess(work([photo(1, EMPTY_PLOT), photo(2, EMPTY_PLOT)]), AS_OF)
    assert r.status == Status.ASSESSED and "ASSET_NOT_SHOWN" in codes(r)
    f = next(f for f in r.findings if f.code == "ASSET_NOT_SHOWN")
    assert f.risk == pytest.approx(agent.NOT_SHOWN_RISK) and "site check" in f.text


def test_one_photo_that_shows_the_building_is_enough():
    r = agent.assess(work([photo(1, EMPTY_PLOT), photo(2, HALL)]), AS_OF)
    assert not codes(r) and r.evidence["claims"]["asset"] == "shown"


def test_a_single_photo_of_bare_ground_is_not_enough_to_say_not_shown():
    r = agent.assess(work([photo(1, EMPTY_PLOT)]), AS_OF)
    assert not codes(r) and r.evidence["claims"]["asset"] == "cant_tell"


def test_a_photo_on_another_work_confirms_nothing_and_counts_against_nothing():
    w = work([photo(1, HALL, sha="shared"), photo(2, EMPTY_PLOT), photo(3, EMPTY_PLOT)])
    other = {"work_id": "W2", "evidence": {"files": [{"sha256": "shared", "ext": "jpg"}]}}
    r = agent.assess(w, AS_OF, PhotoIndex.build([w, other]))
    # the only photo that shows the hall belongs to another work too: what is left is bare ground
    assert "ASSET_NOT_SHOWN" in codes(r)
    assert r.evidence["voided"] == {"P1": "on another work"}


def test_progress_photos_long_before_completion_do_not_count_against_it():
    early = [{"lat": None, "lon": None, "date": "2024-02-01"}]
    w = work([photo(1, EMPTY_PLOT, stamps=early), photo(2, EMPTY_PLOT, stamps=early)])
    r = agent.assess(w, AS_OF)
    assert not codes(r) and r.evidence["claims"]["asset"] == "cant_tell"


def test_a_photo_stamped_before_the_recommendation_confirms_nothing():
    before = [{"lat": None, "lon": None, "date": "2023-08-01"}]
    w = work([photo(1, HALL, stamps=before)])
    r = agent.assess(w, AS_OF)
    assert r.evidence["claims"]["asset"] == "cant_tell" and "P1" in r.evidence["voided"]


def test_lights_pumps_and_goods_are_never_called_missing_from_a_photo():
    nothing = reading("lights", built=0.05, not_built=0.0, not_site=0.10)
    w = work([photo(1, nothing), photo(2, nothing)], wtype="STREET_LIGHT",
             desc="10 solar street lights at Rampur")
    r = agent.assess(w, AS_OF)
    assert not codes(r) and r.evidence["claims"]["asset"] == "cant_tell"


def test_the_decisive_test_a_claim_the_photos_plainly_do_not_show():
    """T503: half-built photos and the claim "roof slab cast" with no roof -> not shown."""
    half = reading("building", built=0.10, not_built=0.85)
    w = work([photo(1, half), photo(2, half)], status="SANCTIONED",
             field_notes=["Roof slab cast"])
    w["evidence"]["site_judgements"] = [
        {"claim": "Roof slab cast", "verdict": "not_shown", "reader": "test",
         "reason": "the walls stand at half height and there is no roof"}]
    r = agent.assess(w, AS_OF)
    f = next(f for f in r.findings if f.code == "CLAIM_NOT_SHOWN")
    assert "Roof slab cast" in f.text and "no roof" in f.text
    assert r.evidence["claims"]["field"] == {"Roof slab cast": "not_shown"}


def test_a_claim_no_reader_judged_is_cant_tell_never_shown():
    w = work([photo(1, HALL)], field_notes=["Plastering done on all walls"])
    r = agent.assess(w, AS_OF)
    assert r.evidence["claims"]["field"] == {"Plastering done on all walls": "cant_tell"}


def test_a_plaque_dated_before_the_recommendation_needs_checking():
    p = {"scheme": True, "dates": [{"label": "start", "date": "2023-10-01"},
                                   {"label": "completion", "date": "2023-12-31"}]}
    w = work([photo(1, HALL | {"plaque": p})])
    r = agent.assess(w, AS_OF)
    f = next(f for f in r.findings if f.code == "PLAQUE_DATED_BEFORE_RECOMMENDATION")
    assert "2023-12-31" in f.text and "2024-01-10" in f.text
    assert r.evidence["plaque"] == "shown"


def test_no_plaque_in_the_photos_is_a_fact_not_a_finding():
    r = agent.assess(work([photo(1, HALL), photo(2, HALL)]), AS_OF)
    assert r.evidence["plaque"] == "not seen" and not codes(r)
    assert "plaque" in r.headline.lower()


def test_text_is_plain_and_risk_bounded_on_every_path():
    for files in ([photo(1, EMPTY_PLOT), photo(2, EMPTY_PLOT)], [photo(1, HALL)]):
        r = agent.assess(work(files), AS_OF)
        assert 0 <= r.risk <= 1
        json.dumps(r.to_json(), default=str)


# ----------------------------------------------------------------- switched off until measured

def test_site_progress_v3_is_the_fourth_agent_and_v2_is_kept_for_the_photo_trial():
    # T125: the engine registers v3 (site videos) in its core slot; the v2 photo judge stays a
    # module for data/trial/site_progress_trial.py and is never run by the pipeline
    from drishti.agents import registry
    from drishti.agents.site_progress import agent as v3
    spec = registry.by_id()["site_progress"]
    assert spec.name == v3.NAME and spec.weight == 0.25 and spec.question == v3.QUESTION
    assert agent.VERSION.startswith("site-progress-2")


# ----------------------------------------------------------------- the optional VLM reader

class FakeTransport:
    def __init__(self, verdicts):
        self.calls, self.verdicts = [], verdicts

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, json.loads(body)))
        text = json.dumps([{"claim": i + 1, "verdict": v, "reason": "seen"}
                           for i, v in enumerate(self.verdicts)])
        return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_vlm_reader_reads_verdicts_caches_and_keeps_the_key_out_of_the_url(tmp_path):
    t = FakeTransport(["shown", "maybe"])
    g = GeminiReader(key="SECRET", ledger=tmp_path / "ledger.json", transport=t)
    out = g.judge(["Roof slab cast", "Walls plastered"], [("sha1", b"\xff\xd8jpeg")])
    assert [j["verdict"] for j in out] == ["shown", "cant_tell"]     # unknown -> can't tell
    url, headers, _body = t.calls[0]
    assert "SECRET" not in url and headers["x-goog-api-key"] == "SECRET"
    again = g.judge(["Roof slab cast", "Walls plastered"], [("sha1", b"\xff\xd8jpeg")])
    assert again == out and len(t.calls) == 1                        # read once, never twice


def test_vlm_reader_stops_at_its_daily_cap(tmp_path):
    g = GeminiReader(key="k", ledger=tmp_path / "ledger.json", daily_cap=1,
                     transport=FakeTransport(["shown"]))
    g.judge(["A"], [("s1", b"x")])
    with pytest.raises(QuotaReached):
        g.judge(["B"], [("s2", b"y")])


def test_vlm_reader_needs_a_key():
    with pytest.raises(ValueError):
        GeminiReader(key="")
