import pytest

from drishti import config


def test_prefers_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://other:p@x:6543/db")
    assert config.database_url() == "postgresql://u:p@h:5432/db"


def test_falls_back_to_the_vercel_supabase_variable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_URL", "postgres://u:p@pooler:6543/postgres?sslmode=require&supa=base-pooler.x")
    assert config.database_url() == "postgres://u:p@pooler:6543/postgres?sslmode=require"


def test_strips_parameters_libpq_rejects():
    url = "postgres://u:p@h:6543/postgres?pgbouncer=true&sslmode=require&supa=base-pooler.x"
    assert config.clean_url(url) == "postgres://u:p@h:6543/postgres?sslmode=require"


def test_missing_url_is_an_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    with pytest.raises(RuntimeError):
        config.database_url()
