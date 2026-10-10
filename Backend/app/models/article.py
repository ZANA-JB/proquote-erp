"""Définit les lignes d'article rattachées à une cotation."""

import uuid

from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    designation = Column(String, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=0)
    unit = Column(String, nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    line_total = Column(Numeric(12, 2), nullable=False, default=0)
    quotation_id = Column(String(36), ForeignKey("quotations.id"), nullable=False)

    quotation = relationship("Quotation", back_populates="articles")
