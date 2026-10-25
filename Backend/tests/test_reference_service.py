from datetime import date
from threading import Barrier, Thread

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, SessionLocal, engine
from app.models.article import Article
from app.models.quotation import Quotation
from app.models.reference_counter import ReferenceCounter
from app.models.user import User
from app.services.reference_service import generate_reference


Base.metadata.create_all(bind=engine)


def test_generate_reference_sequential():
    db = SessionLocal()
    try:
        db.query(ReferenceCounter).delete()
        db.commit()

        first = generate_reference(db, creation_date=date(2026, 7, 30))
        db.commit()

        second = generate_reference(db, creation_date=date(2026, 7, 30))
        db.commit()

        assert first == "001#30-07-2026"
        assert second == "002#30-07-2026"
        assert first != second
    finally:
        db.close()


@pytest.mark.skipif(
    engine.dialect.name == "sqlite",
    reason="SQLite ignores SELECT FOR UPDATE; concurrency locking requires PostgreSQL.",
)
def test_generate_reference_concurrent_simulation():
    db = SessionLocal()
    try:
        db.query(ReferenceCounter).delete()
        db.commit()
    finally:
        db.close()

    barrier = Barrier(2)
    results = []

    def worker():
        local_db = SessionLocal()
        try:
            barrier.wait()
            ref = generate_reference(local_db, creation_date=date(2026, 7, 30))
            local_db.commit()
            results.append(ref)
        finally:
            local_db.close()

    t1 = Thread(target=worker)
    t2 = Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    assert results[0] != results[1]
    assert {"001#30-07-2026", "002#30-07-2026"} == set(results)


def test_generate_reference_skips_existing_reference_when_counter_is_stale():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine)
    db = test_session()

    try:
        db.add(ReferenceCounter(name="quotation_reference_counter", value=2))
        db.add(
            Quotation(
                reference="003#30-07-2026",
                client_name="Existing quotation",
                client_email="existing@example.test",
            )
        )
        db.commit()

        generated = generate_reference(db, creation_date=date(2026, 7, 30))

        assert generated == "004#30-07-2026"
        assert db.query(ReferenceCounter).one().value == 4
    finally:
        db.close()
        test_engine.dispose()
