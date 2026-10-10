"""Définit les dépendances d'authentification et de contrôle des rôles."""

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.database import get_db
from app.models.quotation import Quotation
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or nonexistent user")
    if payload["ver"] != user.token_version:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_role(*roles: UserRole):
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return role_dependency


def require_quotation_access(quotation: Quotation, current_user: User) -> None:
    if current_user.role == UserRole.COLLABORATEUR and quotation.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
