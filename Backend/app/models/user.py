"""Définit le modèle utilisateur et les rôles de l'application."""

import uuid

from sqlalchemy import Column, String, DateTime, Enum, Boolean, Integer
from datetime import datetime
from app.core.database import Base
import enum


class UserRole(enum.Enum):
    COLLABORATEUR = "COLLABORATEUR"
    RESPONSABLE = "RESPONSABLE"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.COLLABORATEUR)
    is_active = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
