from datetime import date
from threading import Barrier, Thread

from app.core.database import Base, SessionLocal, engine
from app.models.reference_counter import ReferenceCounter
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
