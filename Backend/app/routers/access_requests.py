"""Gère les demandes d'accès et leur transformation en comptes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import get_password_hash
from app.models.access_request import AccessRequest, AccessRequestStatus
from app.models.user import User, UserRole
from app.schemas.access_request import (
    AccessProfile,
    AccessRequestCreate,
    AccessRequestOut,
    AccessRequestUpdateStatus,
)

router = APIRouter()


@router.get("/access-requests", response_model=list[AccessRequestOut], dependencies=[Depends(require_role(UserRole.ADMIN))])
def list_access_requests(db: Session = Depends(get_db)):
    return db.query(AccessRequest).order_by(AccessRequest.created_at.desc()).all()


@router.post("/access-requests", response_model=AccessRequestOut)
def create_access_request(payload: AccessRequestCreate, db: Session = Depends(get_db)):
    if payload.profilSouhaite not in (AccessProfile.COMMERCIAL, AccessProfile.MANAGER):
        raise HTTPException(status_code=400, detail="Profil invalide")
    existing_request = db.query(AccessRequest).filter(
        AccessRequest.email == payload.email,
        AccessRequest.status == AccessRequestStatus.EN_ATTENTE,
    ).first()
    if existing_request:
        raise HTTPException(status_code=409, detail="Une demande est déjà en attente pour cet e-mail.")

    request = AccessRequest(
        nomComplet=payload.nomComplet.strip(),
        email=payload.email,
        password_hash=get_password_hash(payload.motDePasse),
        profilSouhaite=payload.profilSouhaite,
        status=AccessRequestStatus.EN_ATTENTE,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.patch("/access-requests/{request_id}/status", response_model=AccessRequestOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def update_access_request_status(
    request_id: str,
    payload: AccessRequestUpdateStatus,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    request.status = payload.status
    db.add(request)

    if payload.status == AccessRequestStatus.ACCEPTEE:
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="Un compte existe déjà pour cet e-mail.")
        role = UserRole.RESPONSABLE if request.profilSouhaite.value == AccessProfile.MANAGER.value else UserRole.COLLABORATEUR
        password_hash = request.password_hash
        if not password_hash.startswith("$pbkdf2-sha256$"):
            password_hash = get_password_hash(password_hash)
        db.add(
            User(
                email=request.email,
                hashed_password=password_hash,
                full_name=request.nomComplet,
                role=role,
                is_active=True,
            )
        )
        request.password_hash = ""
    elif payload.status == AccessRequestStatus.REFUSEE:
        request.password_hash = ""

    db.commit()
    db.refresh(request)
    return request


@router.delete("/access-requests/{request_id}", status_code=204, dependencies=[Depends(require_role(UserRole.ADMIN))])
def delete_access_request(request_id: str, db: Session = Depends(get_db)):
    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    db.delete(request)
    db.commit()
