"""Décrit les données échangées pour les comptes utilisateurs."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=120)
    role: UserRole


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserAvatarUpdate(BaseModel):
    avatar_url: str = Field(max_length=4_200_000)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
