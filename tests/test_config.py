from config import database_uri


def test_database_uri_uses_psycopg_driver_for_render_postgres_url():
    uri = database_uri("postgresql://user:pass@host:5432/db")

    assert uri == "postgresql+psycopg://user:pass@host:5432/db"


def test_database_uri_keeps_explicit_driver_unchanged():
    uri = database_uri("postgresql+psycopg://user:pass@host:5432/db")

    assert uri == "postgresql+psycopg://user:pass@host:5432/db"
