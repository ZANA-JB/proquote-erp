"""Charge les paramètres de l'application depuis l'environnement."""

from pydantic_settings import BaseSettings
from urllib.parse import urlsplit


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./test.db"
    # Les secrets doivent être fournis explicitement dans l'environnement.
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    # L'expéditeur doit être configuré explicitement pour les emails réels.
    MAIL_FROM: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    PDF_STORAGE_PATH: str = "storage/pdfs"
    COMPANY_NAME: str = ""
    COMPANY_ADDRESS: str = ""
    COMPANY_CONTACTS: str = ""
    COMPANY_BANK_DETAILS: str = ""
    COMPANY_LOGO_URL: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"

    def validate_production(self) -> None:
        if self.ENVIRONMENT.lower() != "production":
            return

        if len(self.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY must contain at least 32 characters in production.")
        if not self.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise RuntimeError("DATABASE_URL must point to PostgreSQL in production.")
        if self.ALGORITHM != "HS256":
            raise RuntimeError("ALGORITHM must be HS256 in production.")
        missing_company_settings = [
            name
            for name, value in {
                "COMPANY_NAME": self.COMPANY_NAME,
                "COMPANY_ADDRESS": self.COMPANY_ADDRESS,
                "COMPANY_CONTACTS": self.COMPANY_CONTACTS,
                "COMPANY_BANK_DETAILS": self.COMPANY_BANK_DETAILS,
            }.items()
            if not value.strip()
        ]
        if missing_company_settings:
            raise RuntimeError(
                "PDF company details must be configured in production: "
                + ", ".join(missing_company_settings)
                + "."
            )
        origins = self.allowed_origins
        if not origins:
            raise RuntimeError("ALLOWED_ORIGINS must contain the deployed frontend origin in production.")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or "*" in origin
            ):
                raise RuntimeError("ALLOWED_ORIGINS must contain only valid HTTPS origins in production.")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
