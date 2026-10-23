"""
DocuVerify AI — Application Settings
Loaded from environment variables / .env file.
"""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./docuverify.db"

    # Security
    secret_key: str = "insecure-dev-secret-change-me"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Storage
    storage_dir: str = "../storage"
    max_upload_mb: int = 20

    # OCR
    tesseract_cmd: str = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

    # AI provider
    gemini_api_key: str = ""

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Environment
    environment: str = "development"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def gemini_available(self) -> bool:
        return bool(self.gemini_api_key)


settings = Settings()
