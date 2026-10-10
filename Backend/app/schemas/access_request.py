"""Décrit les demandes d'accès et leurs changements d'état."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class AccessProfile(str, Enum):
    COMMERCIAL = "COMMERCIAL"
    MANAGER = "MANAGER"


class AccessRequestStatus(str, Enum):
    EN_ATTENTE = "EN_ATTENTE"
    ACCEPTEE = "ACCEPTEE"
    REFUSEE = "REFUSEE"


class AccessRequestCreate(BaseModel):
    nomComplet: str = Field(min_length=1, max_length=120)
    email: EmailStr
    motDePasse: str = Field(min_length=12, max_length=128)
    profilSouhaite: AccessProfile


class AccessRequestUpdateStatus(BaseModel):
    status: AccessRequestStatus


class AccessRequestOut(BaseModel):
    id: str
    nomComplet: str
    email: EmailStr
    profilSouhaite: AccessProfile
    status: AccessRequestStatus = AccessRequestStatus.EN_ATTENTE
    created_at: datetime

    model_config = {"from_attributes": True}
