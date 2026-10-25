"""Shared guard that prevents scheduled jobs from running on an outdated schema."""

from app.core.database import engine


def ensure_database_migrations_are_current() -> None:
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    config = Config("alembic.ini")
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    with engine.connect() as connection:
        current_heads = set(MigrationContext.configure(connection).get_current_heads())

    if current_heads != expected_heads:
        raise RuntimeError(
            "Database migrations are not current; refusing to run the scheduled job."
        )
