"""Expose la gestion des comptes utilisateurs réservée aux administrateurs."""

import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.access_request import AccessRequest
from app.models.quotation import Quotation
from app.schemas.user import UserAvatarUpdate, UserCreate, UserOut, UserUpdate
from app.models.audit_log import AuditLog
from app.core.security import get_password_hash

router = APIRouter()


@router.post("/", response_model=UserOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=UserRole(payload.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit = AuditLog(
        user_id=current_user.id,
        action="user.created",
        entity_type="User",
        entity_id=user.id,
        details={"email": user.email, "role": user.role.value},
    )
    db.add(audit)
    db.commit()
    return user


@router.get("/", response_model=list[UserOut], dependencies=[Depends(require_role(UserRole.ADMIN))])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str | None = Query(None, max_length=250),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (User.email.ilike(pattern))
            | (User.full_name.ilike(pattern))
            | (User.role.ilike(pattern))
        )
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None and payload.role != user.role:
        user.role = payload.role
        user.token_version += 1
    if payload.is_active is not None:
        if payload.is_active != user.is_active:
            user.token_version += 1
        user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    audit = AuditLog(
        user_id=current_user.id,
        action="user.updated",
        entity_type="User",
        entity_id=user.id,
        details={"full_name": user.full_name, "role": user.role.value, "is_active": user.is_active},
    )
    db.add(audit)
    db.commit()
    return user


@router.delete("/{user_id}", response_model=UserOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_email = user.email
    db.query(Quotation).filter(Quotation.created_by == user.id).update({Quotation.created_by: None}, synchronize_session=False)
    db.query(AccessRequest).filter(AccessRequest.email == user_email).delete(synchronize_session=False)
    audit = AuditLog(
        user_id=current_user.id,
        action="user.deleted",
        entity_type="User",
        entity_id=user.id,
        details={"email": user_email, "access_requests_deleted": True},
    )
    db.add(audit)
    db.delete(user)
    db.commit()
    user.is_active = False
    return user


@router.patch("/me/avatar", response_model=UserOut)
def update_my_avatar(payload: UserAvatarUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.avatar_url = payload.avatar_url.strip() or None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    audit = AuditLog(
        user_id=current_user.id,
        action="user.avatar_updated",
        entity_type="User",
        entity_id=current_user.id,
        details={"avatar_url": bool(current_user.avatar_url)},
    )
    db.add(audit)
    db.commit()
    return current_user
