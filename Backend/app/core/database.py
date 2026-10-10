"""Configure la connexion SQLAlchemy et les sessions de base de données."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Fournit une session et la ferme après le traitement de la requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
