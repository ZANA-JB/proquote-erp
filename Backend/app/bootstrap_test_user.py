"""Create a least-privilege test collaborator without changing existing accounts."""

from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.tasks.migration_check import ensure_database_migrations_are_current


def create_test_user(email: str, full_name: str, password: str) -> None:
    normalized_email = email.strip().lower()
    normalized_name = full_name.strip()
    if not normalized_email or not normalized_name:
        raise SystemExit("Email and name are required.")
    if len(normalized_name) > 120:
        raise SystemExit("The test user's name must not exceed 120 characters.")
    try:
        normalized_email = str(TypeAdapter(EmailStr).validate_python(normalized_email))
    except ValidationError:
        raise SystemExit("A valid email address is required.") from None
    if len(password) < 12 or len(password) > 128:
        raise SystemExit("The test password must contain between 12 and 128 characters.")

    ensure_database_migrations_are_current()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == normalized_email).first():
            raise SystemExit("A user with this email already exists; no account was changed.")

        db.add(
            User(
                email=normalized_email,
                full_name=normalized_name,
                hashed_password=get_password_hash(password),
                role=UserRole.COLLABORATEUR,
                is_active=True,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Test collaborator created for {normalized_email}. No password was displayed.")


def main() -> None:
    email = input("Test collaborator email: ").strip()
    full_name = input("Test collaborator name: ").strip()
    password = getpass("Temporary password (minimum 12 characters): ")
    confirmation = getpass("Confirm temporary password: ")
    if password != confirmation:
        raise SystemExit("The passwords do not match.")
    create_test_user(email, full_name, password)


if __name__ == "__main__":
    main()
