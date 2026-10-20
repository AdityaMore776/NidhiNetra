"""Replace the works with a new load, keeping what people saved against them (T169).

The works come from the research export and the dashboard tables, rebuilt offline and loaded by
data/load_db.py. The cost forms (migration 013) and site visits (014) are typed in or filmed by
people and exist nowhere else, so a reload must never take them away: Postgres already refuses to
TRUNCATE works while they reference it, and TRUNCATE ... CASCADE would empty them silently.

So the works are replaced in place, in the caller's transaction:
  - every work in the new load is inserted, or updated in full (a column the load does not carry
    is reset to its default, exactly as the old empty-and-refill left it);
  - a work missing from the new load is deleted, unless a saved form or site visit points at it:
    then it stays as it was, and is counted.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

SAVED_INPUT = ("cost_forms", "site_visits")


def replace_works(con, cols: Sequence[str], rows: Iterable[Sequence]) -> dict:
    """Load `rows` (values in `cols` order) as the new set of works. Commit is the caller's."""
    if "work_id" not in cols:
        raise ValueError("the load must carry work_id")
    con.execute("CREATE TEMP TABLE works_new (LIKE works INCLUDING DEFAULTS) ON COMMIT DROP")
    with con.cursor().copy(f"COPY works_new ({', '.join(cols)}) FROM STDIN") as cp:
        for r in rows:
            cp.write_row(r)
    every = {r[0]: r[1] for r in con.execute(
        "SELECT column_name, column_default FROM information_schema.columns WHERE table_schema "
        "= current_schema() AND table_name = 'works' ORDER BY ordinal_position")}
    sets = ", ".join(f"{c} = EXCLUDED.{c}" if c in cols else f"{c} = DEFAULT"
                     for c in every if c != "work_id")
    # rewrite only a work that changed: an unchanged row left alone leaves no dead copy behind
    # (rewriting all 2.1 lakh works grew the database 104 -> 186 MB; the free tier holds 500)
    changed = " OR ".join([f"works.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in cols
                           if c != "work_id"]
                          + [f"works.{c} IS NOT NULL" for c, default in every.items()
                             if c not in cols and default is None])
    names = ", ".join(cols)
    written = con.execute(f"INSERT INTO works ({names}) SELECT {names} FROM works_new "
                          f"ON CONFLICT (work_id) DO UPDATE SET {sets} WHERE {changed}").rowcount
    saved = " OR ".join(f"EXISTS (SELECT 1 FROM {t} s WHERE s.work_id = w.work_id)"
                        for t in SAVED_INPUT)
    gone = "NOT EXISTS (SELECT 1 FROM works_new n WHERE n.work_id = w.work_id)"
    kept = con.execute(f"SELECT count(*) FROM works w WHERE {gone} AND ({saved})").fetchone()[0]
    removed = con.execute(f"DELETE FROM works w WHERE {gone} AND NOT ({saved})").rowcount
    return {"written": written, "removed": removed, "kept_for_saved_input": kept}
