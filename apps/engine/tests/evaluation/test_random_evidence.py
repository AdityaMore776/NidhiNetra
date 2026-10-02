"""The evidence engines in a random environment: malformed papers, photos, stamps and readings.

Evidence facts are stored JSON today and uploads tomorrow (the field app, a citizen's photo). Before
agents/evidence.py, one evidence row whose file was not an object crashed the photo and vendor
indexes, and so the whole batch (found by this test, 2 Oct 2026). Now: no malformed part may stop an
index or an engine, and the answer may not depend on things that carry no evidence (the order files
were attached in, or a junk entry beside the real ones).
"""

import json
import random
from datetime import date, timedelta

import pytest

from drishti.agents import evidence
from drishti.agents.contract import Status
from drishti.agents.paperwork import agent as paperwork
from drishti.agents.photo_evidence import agent as photo
from drishti.agents.photo_evidence.index import PhotoIndex
from drishti.agents.site_progress import agent as site
from drishti.agents.site_progress import observe
from drishti.batch import indexes
from drishti.evaluation.stats import build_store
from drishti.evaluation.synthetic import Generator
from drishti.pipeline.orchestrator import Context, assess_work

AS_OF = date(2026, 5, 26)
JUNK = [None, "", "x", 3, [], {}, [1, 2], float("nan")]


def _pick(rng, *xs):
    return rng.choice(xs)


def _date(rng):
    return _pick(rng, None, "", "2024-13-45", "not a date", 20240101, "2024-02-30T10:00",
                 (AS_OF - timedelta(days=rng.randint(-500, 4000))).isoformat(),
                 AS_OF - timedelta(days=rng.randint(0, 3000)))


def _num(rng):
    return _pick(rng, None, "", 0, -5, 1.5e5, "1,00,000", float("nan"), 4.95e5, "abc", 1e12, True)


def _stamp(rng):
    return _pick(rng, {}, None, "stamp", [1, 2], {
        "lat": _pick(rng, None, 24.5, "24.5", 200.0, float("nan")),
        "lon": _pick(rng, None, 74.6, "x", -10.0), "date": _date(rng),
        "pin": _pick(rng, None, "312001", 312001)})


def _certificate(rng):
    return _pick(rng, {}, None, "c", {
        "sanctioned_amount": _num(rng), "sanction_date": _date(rng),
        "payments": _pick(rng, None, [], [[_date(rng), _num(rng)]], [[_date(rng)]], ["x"], [None],
                          [[None, None]], "pay"),
        "location": _pick(rng, None, "", "Rampur ward 4", 12345, ["a"]),
        "vendor_code": _pick(rng, None, "", "V123456789012", 5)})


def _site(rng):
    g = rng.choice(list(observe.groups()))
    return _pick(rng, None, {}, "x", {
        "version": observe.VERSION,
        "groups": _pick(rng, None, {}, {g: {"built": _num(rng), "not_built": _num(rng),
                                            "not_site": _num(rng)}}),
        "plaque": _pick(rng, None, {}, {"scheme": _pick(rng, True, False, "yes"),
                                        "dates": _pick(rng, None, [], "x", [
                                            {"label": _pick(rng, "start", "completion", None, 5),
                                             "date": _date(rng)}])})})


def _file(rng, i):
    if rng.random() < 0.1:
        return rng.choice(JUNK)
    return {"id": _pick(rng, f"F{i}", None, i, ["x"]),
            "ext": _pick(rng, "pdf", "jpg", "PDF", ".JPG", None, "", "png", 5),
            "sha256": _pick(rng, None, "", f"sha{rng.randint(0, 5)}", 7),
            "pages": _num(rng), "text_lines": _num(rng),
            "readable": _pick(rng, True, False, None, "yes"),
            "stamps": _pick(rng, None, [], [_stamp(rng)], [_stamp(rng), _stamp(rng)], "s"),
            "certificates": _pick(rng, None, [], [_certificate(rng)], "c"),
            "phash": _pick(rng, None, "", "f" * 64, "zz", "F" * 64, 3), "site": _site(rng)}


def _evidence(rng):
    return _pick(rng, None, {}, "ev", {
        "files": _pick(rng, None, [], "x", [_file(rng, i) for i in range(rng.randint(1, 5))]),
        "site_judgements": _pick(rng, None, [], "j", [
            {"claim": _pick(rng, None, "Roof slab cast", 5),
             "verdict": _pick(rng, "shown", "not_shown", "x", None),
             "reason": _pick(rng, None, "the walls stand without a roof", 3)}])})


@pytest.fixture(scope="module")
def messy():
    rng = random.Random(20261002)
    corpus = Generator(seed=3, small=True).build()
    works = corpus.works[:250]
    for w in works:
        w["evidence"] = _evidence(rng)
        w["field_notes"] = _pick(rng, None, [], ["Roof slab cast"], "notes", [None, 5])
    return works, build_store(corpus.works)


def test_malformed_evidence_never_breaks_an_index_or_an_engine(messy):
    works, stats = messy
    ctx = Context(stats=stats, as_of=AS_OF, data=indexes(works))      # must not raise
    photos = ctx.data["photos"]
    for w in works:
        a = assess_work(w, ctx)
        errors = [(r.agent, r.limitations) for r in a.agents if r.status == Status.ERROR]
        assert not errors, (w["work_id"], errors)
        # Site Progress is off in the registry: run it directly on the same mess
        s = site.assess(w, AS_OF, photos)
        assert s.status != Status.ERROR and 0 <= s.risk <= 1
        json.dumps(s.to_json(), default=str)


def test_every_checked_file_has_the_shape_the_engines_read(messy):
    works, _ = messy
    for w in works:
        for f in evidence.files(w):
            assert isinstance(f["id"], str) and isinstance(f["ext"], str)
            assert f["phash"] is None or len(f["phash"]) == 64
            assert all(isinstance(s, dict) for s in f["stamps"])
            for c in f["certificates"]:
                assert c["sanctioned_amount"] is None or isinstance(c["sanctioned_amount"], float)
                assert all(isinstance(a, float) for _d, a in c["payments"])
                assert isinstance(c["location"], str)


def test_indian_digit_grouping_and_junk_numbers():
    assert evidence.num("1,00,000") == 100000.0
    assert evidence.num(" 4,95,000.50 ") == 495000.5
    for junk in (None, "", "abc", float("nan"), float("inf"), True, [1], {}):
        assert evidence.num(junk) is None


def _real_work():
    """One work with a real-shaped photo (stamped), a certificate and a site reading."""
    return {"work_id": "W1", "work_type_code": "COMMUNITY_HALL", "status": "COMPLETED",
            "description": "Construction of community hall at Rampur", "amount": 500000.0,
            "recommended_date": date(2024, 1, 10), "completed_date": date(2024, 6, 1),
            "district_lgd": "", "evidence": {"files": [
                {"id": "P1", "ext": "jpg", "sha256": "s1", "phash": "a" * 64,
                 "stamps": [{"lat": 24.5, "lon": 74.6, "date": "2023-06-01"}],
                 "site": {"version": observe.VERSION, "groups": {
                     "building": {"built": 0.05, "not_built": 0.9, "not_site": 0.05}}}},
                {"id": "P2", "ext": "jpg", "sha256": "s2", "phash": "b" * 64, "stamps": [],
                 "site": {"version": observe.VERSION, "groups": {
                     "building": {"built": 0.05, "not_built": 0.9, "not_site": 0.05}}}},
                {"id": "D1", "ext": "pdf", "sha256": "s3", "readable": True, "certificates": [
                    {"sanctioned_amount": 500000.0, "sanction_date": "2023-11-01",
                     "payments": [["2024-05-01", 650000.0]], "location": "Rampur"}]}]}}


def _answers(w):
    idx = PhotoIndex.build([w])
    out = {}
    for name, r in (("photo", photo.assess(w, AS_OF, idx)), ("paper", paperwork.assess(w)),
                    ("site", site.assess(w, AS_OF, idx))):
        out[name] = (r.status, round(r.risk, 6), sorted(f.code for f in r.findings))
    return out


def test_the_order_files_were_attached_in_changes_nothing():
    w = _real_work()
    base = _answers(w)
    assert base["photo"][2] and base["paper"][2]          # the fixture does raise findings
    files = w["evidence"]["files"]
    for perm in ([2, 1, 0], [1, 2, 0], [2, 0, 1]):
        assert _answers({**w, "evidence": {"files": [files[i] for i in perm]}}) == base


@pytest.mark.parametrize("junk", JUNK + [{"ext": "jpg"}, {"id": "J", "certificates": "x"}])
def test_a_junk_entry_beside_the_real_files_changes_nothing(junk):
    w = _real_work()
    base = _answers(w)
    more = {**w, "evidence": {"files": w["evidence"]["files"] + [junk]}}
    got = _answers(more)
    # a bare photo with no facts is one more photo for Site Progress's counts, never a finding
    assert {k: v[2] for k, v in got.items()} == {k: v[2] for k, v in base.items()}
    assert {k: v[1] for k, v in got.items()} == {k: v[1] for k, v in base.items()}
