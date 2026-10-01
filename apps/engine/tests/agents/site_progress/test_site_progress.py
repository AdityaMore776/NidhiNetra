"""Site Progress (T510): the frame, with a stand-in vision provider (no AI service is called)."""

from drishti.agents.contract import Status
from drishti.agents.site_progress.agent import PLAQUE_CLAIM, assess, satellite_eligible
from drishti.agents.site_progress.provider import Judgement


class FakeVision:
    """Answers from a fixed table: what a vision model would say about these photos."""
    name = "a stand-in provider (tests)"

    def __init__(self, answers: dict[str, str]):
        self.answers = answers

    def judge(self, claims, photos):
        return [Judgement(c, self.answers.get(c, "cant_tell"), "stand-in reason") for c in claims]


def _work(**kw):
    w = {"work_id": "W1", "work_type_code": "COMMUNITY_HALL", "amount": 900_000.0,
         "status": "SANCTIONED", "description": "Community hall at Sitapur",
         "evidence": {"files": [{"id": "1", "ext": "jpg", "sha256": "a"}]},
         "claims": ["Walls built up to lintel level", "Roof slab cast"]}
    w.update(kw)
    return w


def test_the_decisive_test_a_claim_the_photos_plainly_do_not_show():
    # T503's decisive test: half-built photos + "roof slab cast" -> not shown
    v = FakeVision({"Walls built up to lintel level": "shown", "Roof slab cast": "not_shown"})
    r = assess(_work(), v)
    assert r.verdict == "NOT_SHOWN" and "Roof slab cast" in r.headline and r.risk == 0.40


def test_cant_tell_is_never_a_finding():
    r = assess(_work(), FakeVision({}))
    assert r.status == Status.ASSESSED and not r.findings and r.risk == 0


def test_a_reused_photo_voids_every_confirmation():
    v = FakeVision({"Walls built up to lintel level": "shown", "Roof slab cast": "shown"})
    r = assess(_work(), v, reused_photo=True)
    assert r.verdict == "CONFIRMATION_VOID" and r.evidence["shown"] == 0


def test_a_complete_work_without_a_visible_plaque_is_a_note():
    v = FakeVision({"Work complete": "shown", PLAQUE_CLAIM: "not_shown"})
    r = assess(_work(claims=["Work complete"], status="COMPLETED"), v)
    assert r.verdict == "NO_PLAQUE" and r.risk == 0.10


def test_off_without_a_provider_and_not_applicable_without_photos():
    off = assess(_work())
    assert off.status == Status.NOT_ASSESSABLE and "not switched on" in off.headline
    assert assess(_work(evidence={"files": []})).status == Status.NOT_APPLICABLE
    no_claims = assess(_work(claims=[]), FakeVision({}))
    assert no_claims.status == Status.NOT_ASSESSABLE


def test_satellite_is_only_for_big_works():
    assert satellite_eligible({"work_type_code": "POND"})
    assert satellite_eligible({"work_type_code": "ROAD_CC", "description": "CC road 1.2 km"})
    assert not satellite_eligible({"work_type_code": "ROAD_CC", "description": "CC road 300 m"})
    assert satellite_eligible({"work_type_code": "SCHOOL_BUILDING", "amount": 8_000_000})
    assert not satellite_eligible({"work_type_code": "STREET_LIGHT", "amount": 9_000_000})
    r = assess(_work(work_type_code="POND"))
    assert r.evidence["satellite_eligible"] and "not passed" in r.evidence["satellite"]
