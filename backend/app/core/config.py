"""Application Configuration Settings"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # App
    app_name: str = "MantleIQ Discovery Engine"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+psycopg2://mantleiq:mantleiq@db:5432/mantleiq"  # Override with DATABASE_URL env var
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 40

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_log_level: str = "INFO"

    # Frontend
    frontend_url: str = "http://localhost:5173"
    vite_api_url: str = "http://localhost:8000"

    # CORS
    cors_origins: list = ["http://localhost", "http://localhost:5173", "http://localhost:5174", "http://localhost:5178", "http://127.0.0.1:5178"]
    cors_credentials: bool = True
    cors_methods: list = ["*"]
    cors_headers: list = ["*"]

    # Model & Scoring
    model_version: str = "prospectivity_v1"
    ml_model_enabled: bool = False
    rule_model_enabled: bool = True
    confidence_min: float = 0.5
    confidence_max: float = 1.0

    # Grid Parameters
    grid_cell_size_km: float = 10.0
    h3_resolution: int = 5
    dbscan_eps_km: float = 12.0
    dbscan_min_samples: int = 4

    # Export
    pdf_export_enabled: bool = True
    report_generation_timeout: int = 300  # seconds

    # Logging
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # Authentication (Phase 4+)
    oauth_enabled: bool = False
    oauth_provider: str = "google"
    oauth_client_id: str = ""
    oauth_client_secret: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
