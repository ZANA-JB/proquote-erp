"""Point d'entrée de l'API FastAPI et configuration du démarrage."""

import logging
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.routers import auth, users, quotations, articles, dashboard, reminders, access_requests
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.deps import require_role
from app.models.audit_log import AuditLog
from app.models.user import UserRole

app = FastAPI(title="Système de Gestion des Cotations")
logger = logging.getLogger("uvicorn.error")

allowed_origins = settings.allowed_origins or ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def startup_event():
    settings.validate_production()
    Base.metadata.create_all(bind=engine)
    try:
        dialect_name = engine.dialect.name
        logger.info(f"Database dialect detected at startup: {dialect_name}")
    except Exception as exc:
        logger.warning(f"Unable to determine database dialect at startup: {exc}")

    try:
        with engine.connect() as conn:
            if engine.dialect.name == 'sqlite':
                access_table = conn.execute(text("PRAGMA table_info('access_requests')")).mappings().all()
                access_cols = [r['name'] for r in access_table]
                for c in ('motDePasse', 'status'):
                    if c not in access_cols:
                        logger.info(f"Adding missing column to access_requests: {c}")
                        if c == 'status':
                            conn.execute(text("ALTER TABLE access_requests ADD COLUMN status VARCHAR(20) DEFAULT 'EN_ATTENTE' NOT NULL"))
                        else:
                            conn.execute(text(f"ALTER TABLE access_requests ADD COLUMN {c} TEXT"))

                users_table = conn.execute(text("PRAGMA table_info('users')")).mappings().all()
                user_cols = [r['name'] for r in users_table]
                if 'avatar_url' not in user_cols:
                    logger.info("Adding missing column to users: avatar_url")
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))
                if 'token_version' not in user_cols:
                    logger.info("Adding missing column to users: token_version")
                    conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 1 NOT NULL"))

                quotations = conn.execute(text("PRAGMA table_info('quotations')")).mappings().all()
                cols = [r['name'] for r in quotations]
                quotation_columns = {
                    "client_address": "TEXT",
                    "client_reference": "TEXT",
                    "special_conditions": "TEXT",
                    "vat_mode": "VARCHAR(20) DEFAULT 'sans_tva' NOT NULL",
                    "vat_code": "VARCHAR(100)",
                    "vat_rate": "NUMERIC(5, 2)",
                    "payment_method": "VARCHAR(250)",
                    "payment_terms": "VARCHAR(500)",
                }
                for column_name, column_type in quotation_columns.items():
                    if column_name not in cols:
                        logger.info(f"Adding missing column to quotations: {column_name}")
                        conn.execute(
                            text(
                                f"ALTER TABLE quotations ADD COLUMN "
                                f"{column_name} {column_type}"
                            )
                        )
    except Exception as exc:
        logger.warning(f"Runtime migration check failed: {exc}")

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(users.router, prefix="/api/v1/users")
app.include_router(quotations.router, prefix="/api/v1/quotations")
app.include_router(articles.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1/dashboard")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(access_requests.router, prefix="/api/v1")


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "failed", "details": {"database": "failed"}},
        ) from exc

    return {"status": "ok", "details": {"database": "ok"}}


@app.get("/system/tasks-health", dependencies=[Depends(require_role(UserRole.ADMIN))])
def system_tasks_health(db=Depends(get_db)):
    task_entries = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "system_task")
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "tasks": [
            {
                "task_name": entry.entity_id,
                "status": entry.details.get("status") if entry.details else None,
                "processed": entry.details.get("processed") if entry.details else None,
                "timestamp": entry.created_at.isoformat(),
            }
            for entry in task_entries
        ]
    }


@app.get("/system/smtp-check", dependencies=[Depends(require_role(UserRole.ADMIN))])
def system_smtp_check():
    from app.services.email_service import _open_smtp_connection

    if not settings.SMTP_HOST:
        raise HTTPException(status_code=400, detail="SMTP host is not configured")

    try:
        server = _open_smtp_connection()
        server.noop()
        server.quit()
        return {"smtp": "ok"}
    except Exception:
        logger.exception("SMTP connectivity check failed")
        raise HTTPException(status_code=503, detail="SMTP connectivity check failed")
