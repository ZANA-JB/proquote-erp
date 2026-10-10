"""Génère les références séquentielles des cotations."""

from datetime import date
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.reference_counter import ReferenceCounter

REFERENCE_COUNTER_NAME = "quotation_reference_counter"


def generate_reference(db: Session, creation_date: date | None = None) -> str:
    creation_date = creation_date or date.today()

    query = select(ReferenceCounter).where(ReferenceCounter.name == REFERENCE_COUNTER_NAME).with_for_update()
    counter = db.execute(query).scalar_one_or_none()

    if counter is None:
        counter = ReferenceCounter(name=REFERENCE_COUNTER_NAME, value=1)
        db.add(counter)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            counter = db.execute(query).scalar_one()
            counter.value += 1
            db.add(counter)
            db.flush()
    else:
        counter.value += 1
        db.add(counter)
        db.flush()

    return f"{counter.value:03d}#{creation_date.strftime('%d-%m-%Y')}"
