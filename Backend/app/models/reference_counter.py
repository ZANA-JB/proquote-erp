from sqlalchemy import Column, String, Integer
from app.core.database import Base


class ReferenceCounter(Base):
    __tablename__ = "reference_counters"

    name = Column(String(50), primary_key=True, nullable=False)
    value = Column(Integer, nullable=False, default=0)
