"""Photo Evidence (T310): stamp reader, place, time and reuse checks on synthetic facts."""

from datetime import date

from drishti.agents.contract import Status
from drishti.agents.photo_evidence import geo
from drishti.agents.photo_evidence.agent import assess
from drishti.agents.photo_evidence.fingerprint import bits_apart, same_picture
from drishti.agents.photo_evidence.index import PhotoIndex
from drishti.agents.photo_evidence.stamp import read_stamp

AS_OF = date(2026, 9, 26)


def _inside(code: str) -> tuple[float, float]:
    """A point inside a district's outline (a vertex nudged toward the centre)."""
    geom = geo.outlines()[code]["geometry"]
    ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    for t in (0.0, 0.25, 0.5, 0.75):
        x, y = cx + t * (ring[0][0] - cx), cy + t * (ring[0][1] - cy)
        if geo.contains(geom, y, x):
            return y, x
    raise AssertionError("no inside point found")


CODE = next(iter(geo.outlines()))


def _work(**kw):
    w = {"work_id": "W1", "district_lgd": CODE, "recommended_date": date(2025, 1, 10),
         "completed_date": date(2025, 6, 1), "status": "COMPLETED"}
    w.update(kw)
    return w


def _photo(sha="a" * 64, phash=None, stamps=(), source=None):
    f = {"id": "1.1", "ext": "jpg", "sha256": sha, "phash": phash, "stamps": list(stamps)}
    if source:
        f["source"] = source
    return f


def _ev(*files):
    return {"evidence": {"files": list(files)}}


def test_stamp_reader_reads_gps_map_camera_and_fixes_a_misread_year_by_weekday():
    s = read_stamp("GPS Map Camera Rampur, Uttar Pradesh 244901 India Lat 28.81234 "
                   "Long 79.02567 Thursday, 19/10/2023 09:44 AM", latest=AS_OF)
    assert (s["lat"], s["lon"], s["pin"]) == (28.81234, 79.02567, "244901")
    # 19/10/2023 was a Thursday: kept as read
    assert s["date"] == date(2023, 10, 19) and s["date_has_time"] and s["app_named"]
    wrong = read_stamp("Lat 28.81234 Long 79.02567 Thursday, 17/10/2025 09:44", latest=AS_OF)
    assert wrong["date"] == date(2024, 10, 17) and wrong["date_fixed_by_weekday"]


def test_a_painted_plaque_date_loses_to_the_timed_stamp_and_the_year_window_moves():
    s = read_stamp("Date of commencement 12/08/2025 Lat 21.12345 Long 79.12345 "
                   "03/02/2026 10:15 AM", latest=AS_OF)
    assert s["date"] == date(2026, 2, 3)
    # T051: the trial stopped at 31 Dec 2026; a 2028 stamp is read when "today" is 2028
    later = read_stamp("Lat 21.12345 Long 79.12345 05/03/2028 10:15", latest=date(2028, 6, 1))
    assert later["date"] == date(2028, 3, 5)


def test_photo_inside_its_district_with_dates_in_the_window_fits_the_record():
    lat, lon = _inside(CODE)
    r = assess(_work() | _ev(_photo(stamps=[{"lat": lat, "lon": lon, "date": "2025-03-01"}])),
               AS_OF, PhotoIndex())
    assert r.status == Status.ASSESSED and r.risk == 0 and r.evidence["inside"] == 1


def test_photo_far_outside_the_district_is_a_finding():
    own = geo.outlines()[CODE]["geometry"]
    for other in geo.outlines():
        if other == CODE:
            continue
        lat, lon = _inside(other)
        if geo.km_outside(own, lat, lon) > 50:
            break
    r = assess(_work() | _ev(_photo(stamps=[{"lat": lat, "lon": lon}])), AS_OF, PhotoIndex())
    assert r.verdict == "PHOTO_OUTSIDE_DISTRICT" and "km outside" in r.headline


def test_photo_stamped_before_the_recommendation_needs_checking():
    lat, lon = _inside(CODE)
    r = assess(_work() | _ev(_photo(stamps=[{"lat": lat, "lon": lon, "date": "2024-11-02"}])),
               AS_OF, PhotoIndex())
    assert r.verdict == "PHOTO_BEFORE_RECOMMENDATION" and r.risk == 0.40


def test_the_same_photo_on_two_works_and_a_combined_paper_that_is_not():
    a = _work(work_id="A") | _ev(_photo(sha="s1"))
    b = _work(work_id="B") | _ev(_photo(sha="s1"))
    combined = {"id": "9", "ext": "pdf", "sha256": "s2", "pages": 6, "text_lines": 355}
    c = _work(work_id="C") | _ev(combined)
    d = _work(work_id="D") | _ev(dict(combined))
    idx = PhotoIndex.build([a, b, c, d])
    r = assess(a, AS_OF, idx)
    assert r.verdict == "SAME_PHOTO_ON_ANOTHER_WORK" and "B" in r.headline
    assert assess(c, AS_OF, idx).risk == 0                 # a bulk invoice on 2 works: normal
    single = {"id": "8", "ext": "pdf", "sha256": "s3", "pages": 2, "text_lines": 39}
    e, f = _work(work_id="E") | _ev(single), _work(work_id="F") | _ev(dict(single))
    r = assess(e, AS_OF, PhotoIndex.build([e, f]))
    assert r.verdict == "SAME_FILE_ON_ANOTHER_WORK"


def test_an_edited_copy_is_found_by_fingerprint():
    h1 = "f" * 64
    h2 = "f" * 60 + "0000"                                 # 16 bits apart
    assert bits_apart(h1, h2) == 16 and same_picture(h1, h2)
    a = _work(work_id="A") | _ev(_photo(sha="x1", phash=h1))
    b = _work(work_id="B") | _ev(_photo(sha="x2", phash=h2))
    r = assess(a, AS_OF, PhotoIndex.build([a, b]))
    assert r.verdict == "SAME_PHOTO_ON_ANOTHER_WORK"
    assert r.findings[0].evidence["how"] == "fingerprint"


def test_a_citizen_photo_meets_the_same_checks_and_says_it_is_a_demo():
    lat, lon = _inside(CODE)
    r = assess(_work() | _ev(_photo(stamps=[{"lat": lat, "lon": lon, "date": "2024-11-02"}],
                                    source="citizen")), AS_OF, PhotoIndex())
    assert r.verdict == "PHOTO_BEFORE_RECOMMENDATION"
    assert any("citizen" in lim for lim in r.limitations)


def test_nothing_attached_is_not_applicable_and_papers_only_are_checked_for_reuse():
    assert assess(_work(), AS_OF, PhotoIndex()).status == Status.NOT_APPLICABLE
    paper = {"id": "7", "ext": "pdf", "sha256": "p", "pages": 1, "text_lines": 10}
    r = assess(_work() | _ev(paper), AS_OF, PhotoIndex())
    assert r.status == Status.ASSESSED and r.verdict == "NO_PHOTO"
