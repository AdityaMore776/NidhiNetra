"""T169: a reload of the works keeps every saved cost form and site visit (drishti/reload.py).

data/load_db.py used to TRUNCATE works, which Postgres refuses once cost_forms and site_visits
reference it (migrations 013, 014). The works are now replaced in place.
"""

from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from drishti import reload

COLS = ["work_id", "source", "district_lgd", "description", "amount", "status"]


def _row(wid, desc="CC road", amount=100_000, status="SANCTIONED"):
    return {"work_id": wid, "source": "REAL", "district_lgd": "639", "description": desc,
            "amount": amount, "status": status}


def _seed(url):
    with psycopg.connect(url) as con:
        for wid in ("W-1", "W-2", "W-FORM", "W-VISIT"):
            con.execute("INSERT INTO works (work_id, source, district_lgd, description, amount, "
                        "status, sanction_date) VALUES (%s, 'REAL', '639', 'old', 1, "
                        "'RECOMMENDED', '2026-01-01')", (wid,))
        con.execute("INSERT INTO cost_forms (work_id, status, form) "
                    "VALUES ('W-FORM', 'submitted', %s)", (Jsonb({"lines": []}),))
        con.execute("INSERT INTO site_visits (visit_id, work_id, kind) "
                    "VALUES ('V-1', 'W-VISIT', 'baseline')")


def test_a_reload_updates_works_in_place_and_keeps_saved_forms_and_visits(migrated_url):
    _seed(migrated_url)
    rows = [_row("W-1", "CC road, Bijdih", 200_000), _row("W-FORM"), _row("W-VISIT"),
            _row("W-NEW")]
    with psycopg.connect(migrated_url) as con:
        out = reload.replace_works(con, COLS, ([r[c] for c in COLS] for r in rows))
    assert out == {"written": 4, "removed": 1, "kept_for_saved_input": 0}
    with psycopg.connect(migrated_url) as con:
        works = {r[0]: r[1:] for r in con.execute(
            "SELECT work_id, description, amount, status, sanction_date FROM works")}
        forms = con.execute("SELECT count(*) FROM cost_forms").fetchone()[0]
        visits = con.execute("SELECT count(*) FROM site_visits").fetchone()[0]
    assert set(works) == {"W-1", "W-FORM", "W-VISIT", "W-NEW"}       # W-2 left the source
    # every column comes from the new load; a column the load does not carry is reset, as
    # the old empty-and-refill did, never left from the previous load
    assert works["W-1"] == ("CC road, Bijdih", 200_000, "SANCTIONED", None)
    assert forms == 1 and visits == 1


def test_a_work_gone_from_the_source_stays_while_it_has_a_saved_form_or_visit(migrated_url):
    _seed(migrated_url)
    with psycopg.connect(migrated_url) as con:
        out = reload.replace_works(con, COLS, ([r[c] for c in COLS] for r in [_row("W-1")]))
        left = {r[0] for r in con.execute("SELECT work_id FROM works")}
        forms = con.execute("SELECT count(*) FROM cost_forms").fetchone()[0]
    assert out == {"written": 1, "removed": 1, "kept_for_saved_input": 2}
    assert left == {"W-1", "W-FORM", "W-VISIT"} and forms == 1


def test_a_failed_reload_changes_nothing(migrated_url):
    _seed(migrated_url)
    bad = [["W-1", None, "639", "x", 1, "SANCTIONED"]]          # source is NOT NULL
    with psycopg.connect(migrated_url) as con:
        try:
            reload.replace_works(con, COLS, iter(bad))
        except psycopg.Error:
            con.rollback()
        n = con.execute("SELECT count(*) FROM works WHERE description = 'old'").fetchone()[0]
    assert n == 4


def test_migration_016_wiped_the_test_forms_and_visits_once(db_url):
    """The forms and visits saved before 20 Oct 2026 were test data (owner): migration 016 deletes
    them, and like every migration it runs once per database, so later saves are never wiped."""
    from pathlib import Path

    from drishti import migrate

    files = sorted(p.name for p in Path(migrate.MIGRATIONS).glob("*.sql"))
    wipe = next(f for f in files if f.startswith("016_"))
    with psycopg.connect(db_url) as con:                  # a database at 015, with saved input
        con.execute("CREATE TABLE schema_migrations (name text PRIMARY KEY, "
                    "applied_at timestamptz NOT NULL DEFAULT now())")
    _apply_until(db_url, wipe)
    _seed(db_url)
    assert migrate.apply(db_url) == [wipe] + [f for f in files if f > wipe]
    with psycopg.connect(db_url) as con:
        assert con.execute("SELECT count(*) FROM cost_forms").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM site_visits").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM works").fetchone()[0] == 4    # works stay
    _seed_input_only(db_url)
    assert migrate.apply(db_url) == []                      # never again
    with psycopg.connect(db_url) as con:
        assert con.execute("SELECT count(*) FROM cost_forms").fetchone()[0] == 1


def _apply_until(url, stop):
    from pathlib import Path

    from drishti import migrate

    with psycopg.connect(url) as con:
        for p in sorted(Path(migrate.MIGRATIONS).glob("*.sql")):
            if p.name >= stop:
                break
            con.execute(p.read_text(encoding="utf-8"))
            con.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (p.name,))


def _seed_input_only(url):
    with psycopg.connect(url) as con:
        con.execute("INSERT INTO cost_forms (work_id, status, form) "
                    "VALUES ('W-FORM', 'submitted', %s)", (Jsonb({"lines": []}),))
