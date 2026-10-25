"""Run quotation expiry only after the database schema has been migrated."""

from app.tasks.migration_check import ensure_database_migrations_are_current
from app.tasks.expire_quotations import expire_quotations


def main() -> None:
    ensure_database_migrations_are_current()
    processed = expire_quotations.run()
    print(f"Quotation expiry completed; quotations expired: {processed}")


if __name__ == "__main__":
    main()
