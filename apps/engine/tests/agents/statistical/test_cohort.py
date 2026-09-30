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


def test_a_database_returning_fewer_digits_gives_the_same_verdict():
    # hosted Postgres: 15 significant digits; local: 17. At exactly twice the top of the
    # range (Rs 3,10,000 vs Rs 1,55,000) that last digit flipped the verdict.
    from datetime import date

    from drishti.agents.statistical.agent import assess

    def store(p90):
        rows = [{"level": lvl, "work_type_code": "STREET_LIGHT|MAST", "key": key, "n": n,
                 "p10": 5.128837863996165, "p50": 5.1303337684950066, "p90": p90, "sd": 0.2}
                for lvl, key, n in (("type_district", "533", 152), ("type_state", "36", 2046),
                                    ("type", "", 26384))]
        return StatsStore.from_rows(rows, [], [])

    local, hosted = store(5.190331698170292), store(5.19033169817029)
    assert local.chain("STREET_LIGHT|MAST", "533", "36")[0].p90 == \
        hosted.chain("STREET_LIGHT|MAST", "533", "36")[0].p90
    work = {"work_id": "W", "amount": 310000.0, "work_type_code": "STREET_LIGHT",
            "district_lgd": "533", "state_lgd": "36", "district_name": "Nizamabad",
            "description": "Installation of 2 High Mast Lights near Ramalayam Temple",
            "status": "RECOMMENDED", "recommended_date": date(2025, 1, 1)}
    a, b = (assess(dict(work), s, date(2026, 5, 26)) for s in (local, hosted))
    assert (a.verdict, a.risk) == (b.verdict, b.risk)
