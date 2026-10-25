"""Initialise ou met à jour les comptes par défaut et les données de démonstration."""

import os
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.article import Article
from app.models.quotation import Quotation, QuotationStatus
from app.models.user import User, UserRole
from app.services.reference_service import generate_reference


def _ensure_demo_seeding_is_allowed() -> None:
    if settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError("Demo seeding is disabled in production.")


def seed_admin(password: str):
    _ensure_demo_seeding_is_allowed()
    if not password:
        raise ValueError("A seed password must be provided at runtime.")

    password_hash = get_password_hash(password)
    db: Session = SessionLocal()
    try:
        seeded_users = [
            {
                "email": "admin@example.com",
                "full_name": "Admin",
                "role": UserRole.ADMIN,
            },
            {
                "email": "admin@tridentoil.com",
                "full_name": "Jean Administrateur",
                "role": UserRole.ADMIN,
            },
            {
                "email": "manager@example.com",
                "full_name": "Manager",
                "role": UserRole.RESPONSABLE,
            },
            {
                "email": "collab@example.com",
                "full_name": "Collaborateur",
                "role": UserRole.COLLABORATEUR,
            },
        ]

        for seeded_user in seeded_users:
            user = db.query(User).filter(User.email == seeded_user["email"]).first()
            if user:
                user.hashed_password = password_hash
                user.full_name = seeded_user["full_name"]
                user.role = seeded_user["role"]
                user.is_active = True
                db.add(user)
                continue

            db.add(
                User(
                    email=seeded_user["email"],
                    hashed_password=password_hash,
                    full_name=seeded_user["full_name"],
                    role=seeded_user["role"],
                    is_active=True,
                )
            )

        db.commit()
    finally:
        db.close()

def seed_demo_quotations() -> None:
    _ensure_demo_seeding_is_allowed()
    db: Session = SessionLocal()
    try:
        users = {
            UserRole.ADMIN: db.query(User).filter(User.role == UserRole.ADMIN).all(),
            UserRole.RESPONSABLE: db.query(User).filter(User.role == UserRole.RESPONSABLE).all(),
            UserRole.COLLABORATEUR: db.query(User).filter(User.role == UserRole.COLLABORATEUR).all(),
        }

        statuses = [
            QuotationStatus.BROUILLON,
            QuotationStatus.ENVOYEE,
            QuotationStatus.ACCEPTEE,
            QuotationStatus.REFUSEE,
            QuotationStatus.EXPIREE,
        ]

        for role, role_users in users.items():
            if not role_users:
                continue
            for index in range(25):
                creator = role_users[index % len(role_users)]
                creation_day = date.today() - timedelta(days=index * 2)
                status = statuses[index % len(statuses)]
                quotation = Quotation(
                    client_name=f"Client {role.value} {index + 1}",
                    client_email=f"client{role.value.lower()}_{index + 1}@example.com",
                    client_address=f"{index + 10} Rue Exemple, {index + 1} 000",
                    client_reference=f"REF-{role.value[:3].upper()}-{index + 1:03d}",
                    creation_date=creation_day,
                    validity_date=creation_day + timedelta(days=30),
                    delivery_duration="7 jours",
                    incoterm="CLIENT",
                    special_conditions="Conditions standard",
                    status=status,
                    total_amount=(index + 1) * 125.0,
                    created_by=creator.id,
                )
                db.add(quotation)
                db.flush()
                quotation.reference = quotation.reference or generate_reference(db, creation_date=quotation.creation_date)
                article = Article(
                    designation=f"Prestation {role.value} {index + 1}",
                    quantity=(index % 5) + 1,
                    unit="u",
                    unit_price=(index + 1) * 25.0,
                    line_total=((index % 5) + 1) * ((index + 1) * 25.0),
                    quotation=quotation,
                )
                db.add(article)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_password = os.environ.get("SEED_DEFAULT_PASSWORD", "")
    if not seed_password:
        raise SystemExit("Set SEED_DEFAULT_PASSWORD in the environment to seed demo users.")
    seed_admin(seed_password)
    seed_demo_quotations()
    print("Demo users and quotations created.")
