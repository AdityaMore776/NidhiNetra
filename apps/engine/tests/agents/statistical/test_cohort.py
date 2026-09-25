import psycopg
import pytest

from drishti.agents.statistical.cohort import StatsStore


def _row(level, key, n, p50=5.3):
    return {"level": level, "work_type_code": "ROAD_CC", "key": key, "n": n,
            "p10": p50 - 0.3, "p50": p50, "p90": p50 + 0.3, "sd": 0.25}


@pytest.fixture()
def store():
    return StatsStore.from_rows(
        cohorts=[_row("type_district", "639", 40, 5.1), _row("type_state", "24", 300, 5.2),
                 _row("type", "", 49000, 5.3)],
        durations=[{"work_type_code": "ROAD_CC", "n": 500, "p50": 380, "p90": 700,
                    "p98": 900}],
        unit_models=[])


def test_district_cohort_first(store):
    c = store.cohort("ROAD_CC", "639", "24")
    assert c.level == "type_district" and c.n == 40 and c.p50 == 5.1


def test_backs_off_to_state_then_country(store):
    assert store.cohort("ROAD_CC", "999", "24").level == "type_state"
    assert store.cohort("ROAD_CC", "999", "99").level == "type"


def test_unknown_type_has_no_cohort(store):
    assert store.cohort("BRIDGE", "639", "24") is None
    assert store.cohort(None, "639", "24") is None


def test_small_cohorts_are_skipped():
    s = StatsStore.from_rows(cohorts=[_row("type_district", "639", 12), _row("type", "", 30)],
                             durations=[], unit_models=[])
    assert s.cohort("ROAD_CC", "639", "24").level == "type"


def test_duration_norm(store):
    assert store.p98("ROAD_CC") == 900
    assert store.p98("BRIDGE") is None


def test_loads_from_the_database(migrated_url):
    with psycopg.connect(migrated_url) as con:
        con.execute("INSERT INTO cohort_stats VALUES ('type','ROAD_CC','',100,5,5.3,5.6,0.24)")
        con.execute("INSERT INTO duration_stats VALUES ('ROAD_CC',100,380,700,900)")
        con.commit()
    s = StatsStore.load(migrated_url)
    assert s.cohort("ROAD_CC", "1", "2").n == 100
    assert s.p98("ROAD_CC") == 900


def test_timeline_rates_come_from_the_database(migrated_url):
    with psycopg.connect(migrated_url) as con:
        con.execute("INSERT INTO timeline_quarters VALUES "
                    "('2024-Q1', 25086, 443), ('2024-Q3', 3719, 18)")
        con.execute("INSERT INTO timeline_agencies VALUES ('Office A', 400, 85)")
        con.commit()
    s = StatsStore.load(migrated_url)
    assert s.timeline.overall == pytest.approx(461 / 28805)
    assert s.timeline.agency_concentration("Office A").bad == 85


def test_no_timeline_tables_means_no_rates():
    s = StatsStore.from_rows(cohorts=[], durations=[], unit_models=[])
    assert s.timeline is None
