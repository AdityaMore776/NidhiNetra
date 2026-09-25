r"""Create the three demo accounts in Supabase Auth and give each a DRISHTI role.

Needs SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and DATABASE_URL in the
environment (never in a file that is committed). Passwords are generated here,
printed ONCE, and not stored anywhere by this script.

Run:
  apps\engine\.venv\Scripts\python.exe data\seed_users.py --district 546
"""

from __future__ import annotations

import argparse
import os
import secrets

import httpx
import psycopg

USERS = [
    ("ministry@drishti.demo", "MINISTRY", "Ministry reviewer", False),
    ("district@drishti.demo", "DISTRICT", "District officer", True),
    ("field@drishti.demo", "FIELD", "Field officer", True),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", required=True, help="LGD code for the district officer")
    args = ap.parse_args()
    url, key = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as con:
        for email, role, name, scoped in USERS:
            password = secrets.token_urlsafe(10)
            r = httpx.post(f"{url}/auth/v1/admin/users", headers=headers, timeout=30,
                           json={"email": email, "password": password, "email_confirm": True})
            if r.status_code == 422:        # already exists: reset its password
                users = httpx.get(f"{url}/auth/v1/admin/users", headers=headers,
                                  timeout=30).json()["users"]
                uid = next(u["id"] for u in users if u["email"] == email)
                httpx.put(f"{url}/auth/v1/admin/users/{uid}", headers=headers, timeout=30,
                          json={"password": password}).raise_for_status()
            else:
                r.raise_for_status()
                uid = r.json()["id"]
            con.execute(
                "INSERT INTO profiles (user_id, role, district_lgd, display_name) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET role = "
                "EXCLUDED.role, district_lgd = EXCLUDED.district_lgd, "
                "display_name = EXCLUDED.display_name",
                (uid, role, args.district if scoped else None, name))
            print(f"{role:9} {email:26} {password}")
        con.commit()


if __name__ == "__main__":
    main()
