"""Expose la connexion et la consultation du profil authentifié."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password, verify_password_and_update
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, PasswordChangeRequest, TokenResponse, UserOut
from app.models.audit_log import AuditLog

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        password_matches, upgraded_hash = verify_password_and_update(payload.password, user.hashed_password)
    except (TypeError, ValueError):
        password_matches = False
        upgraded_hash = None

    if not password_matches:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if upgraded_hash:
        user.hashed_password = upgraded_hash
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "role": user.role.value, "ver": user.token_version})
    audit = AuditLog(
        user_id=user.id,
        action="auth.login",
        entity_type="User",
        entity_id=user.id,
        details={"email": user.email},
    )
    db.add(audit)
    db.commit()
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.token_version += 1
    db.add(current_user)
    db.commit()
    return {"message": "Déconnexion effectuée."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.old_password or not payload.new_password or not payload.confirm_password:
        raise HTTPException(status_code=400, detail="Tous les champs de mot de passe sont requis.")

    try:
        password_matches = verify_password(payload.old_password, current_user.hashed_password)
    except (TypeError, ValueError):
        password_matches = False

    if not password_matches:
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect.")

    if len(payload.new_password) < 12:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 12 caractères.")

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="La confirmation du nouveau mot de passe ne correspond pas.")

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.token_version += 1
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    audit = AuditLog(
        user_id=current_user.id,
        action="user.password_changed",
        entity_type="User",
        entity_id=current_user.id,
        details={"email": current_user.email},
    )
    db.add(audit)
    db.commit()

    token = create_access_token({"sub": current_user.id, "role": current_user.role.value, "ver": current_user.token_version})
    return {"message": "Mot de passe modifié avec succès.", "access_token": token, "token_type": "bearer"}
