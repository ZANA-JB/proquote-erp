"""Run scheduled payment reminders after validating database and mail settings."""

from app.core.config import settings
from app.tasks.migration_check import ensure_database_migrations_are_current
from app.tasks.payment_reminders import send_payment_reminders


def main() -> None:
    ensure_database_migrations_are_current()
    missing_mail_settings = [
        name
        for name, value in {
            "SMTP_HOST": settings.SMTP_HOST,
            "MAIL_FROM": settings.MAIL_FROM,
        }.items()
        if not value.strip()
    ]
    if missing_mail_settings:
        raise RuntimeError(
            "Scheduled payment reminders require: "
            + ", ".join(missing_mail_settings)
            + "."
        )

    result = send_payment_reminders.run()
    print(
        "Payment reminders completed; "
        f"sent: {result['sent']}, failed: {result['failed']}"
    )


if __name__ == "__main__":
    main()
