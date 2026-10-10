"""Create the first production administrator without storing credentials in source."""

from getpass import getpass

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole


def main() -> None:
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator name: ").strip()
    password = getpass("Administrator password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")

    if not email or not full_name:
        raise SystemExit("Email and name are required.")
    if len(password) < 12:
        raise SystemExit("The administrator password must contain at least 12 characters.")
    if password != confirmation:
        raise SystemExit("The passwords do not match.")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == UserRole.ADMIN).first():
            raise SystemExit("An administrator already exists; no account was changed.")
        if db.query(User).filter(User.email == email).first():
            raise SystemExit("This email already belongs to an account; no account was changed.")

        db.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Initial administrator created.")


if __name__ == "__main__":
    main()
