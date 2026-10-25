"""Create the first administrator or reset one existing administrator's password."""

from getpass import getpass
from typing import Literal

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole


def configure_admin_account(email: str, full_name: str, password: str) -> Literal["created", "reset"]:
    normalized_email = email.strip().lower()
    normalized_name = full_name.strip()
    try:
        normalized_email = str(TypeAdapter(EmailStr).validate_python(normalized_email))
    except ValidationError:
        raise SystemExit("A valid administrator email address is required.") from None

    if len(password) < 12 or len(password) > 128:
        raise SystemExit("The administrator password must contain between 12 and 128 characters.")

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email == normalized_email)
            .with_for_update()
            .one_or_none()
        )
        if user is not None:
            if user.role != UserRole.ADMIN:
                raise SystemExit("This email belongs to a non-administrator; no account was changed.")
            if not user.is_active:
                raise SystemExit("This administrator is inactive; no account was changed.")

            user.hashed_password = get_password_hash(password)
            user.token_version += 1
            db.commit()
            return "reset"

        if db.query(User).filter(User.role == UserRole.ADMIN).first():
            raise SystemExit(
                "An administrator already exists. Enter that administrator's exact email to reset its password."
            )
        if not normalized_name:
            raise SystemExit("Administrator name is required when creating the first account.")
        if len(normalized_name) > 120:
            raise SystemExit("The administrator name must not exceed 120 characters.")

        db.add(
            User(
                email=normalized_email,
                hashed_password=get_password_hash(password),
                full_name=normalized_name,
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        db.commit()
        return "created"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator name (used only when creating the first account): ").strip()
    confirmation = input(f"Type {email} to confirm the create/reset operation: ").strip().lower()
    if confirmation != email:
        raise SystemExit("Email confirmation did not match; no account was changed.")

    password = getpass("Administrator password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        raise SystemExit("The passwords do not match.")

    result = configure_admin_account(email, full_name, password)
    if result == "reset":
        print("Administrator password reset. Existing sessions for this account are invalidated.")
    else:
        print("Initial administrator created.")


if __name__ == "__main__":
    main()
