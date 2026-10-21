"""The loophole registry stays usable (T171, data/eval/loopholes/; the owner, 20 Oct 2026).

Every hand-written entry has a known state and a unique id, says what happens today, and a fix's
guard that names a test points at a test file that exists. The open entries' scenarios still show
them open (when one starts being caught, the registry must be updated, not left saying "open")."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "data" / "eval" / "common"))
sys.path.insert(0, str(ROOT / "data" / "eval" / "loopholes"))
import world  # noqa: E402,F401,I001  (first: it sets the paths)
import manual as M  # noqa: E402

STATES = {"fixed", "mitigated", "limit", "open", "pending", "holds"}


def test_every_entry_has_a_state_an_id_and_says_what_happens_today():
    ids = [e.id for e in M.ENTRIES]
    assert len(ids) == len(set(ids)), "registry ids must be unique"
    for e in M.ENTRIES:
        assert e.state in STATES, e.id
        assert e.title and e.found and e.now, e.id
        assert e.state != "fixed" or e.guard, f"{e.id}: a fix names the test that keeps it"
        assert e.state != "holds" or (ROOT / e.guard).exists(), f"{e.id}: names its result file"


@pytest.mark.parametrize("entry", [e for e in M.ENTRIES if e.guard.startswith("tests/")],
                         ids=lambda e: e.id)
def test_a_guard_test_exists(entry):
    path = ROOT / "apps" / "engine" / entry.guard.split("::")[0]
    assert path.exists(), f"{entry.id}: {path} not found"
    if "::" in entry.guard:
        assert f"def {entry.guard.split('::')[1]}(" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("entry", [e for e in M.ENTRIES if e.run is not None], ids=lambda e: e.id)
def test_a_runnable_entry_still_behaves_as_registered(entry):
    got, said = entry.run()
    want = "missed" if entry.state in ("open", "limit") else "caught"
    assert got == want, (f"{entry.id} is registered '{entry.state}' but its scenario now says "
                         f"'{got}' ({said}): update data/eval/loopholes/manual.py and re-run "
                         "check.py")
