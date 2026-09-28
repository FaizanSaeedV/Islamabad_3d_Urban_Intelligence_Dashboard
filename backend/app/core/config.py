"""Application configuration loaded from environment variables (.env)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root (three levels up from backend/app/core/config.py).
# The .env file lives at the repo root; also accept a local ./.env so the
# backend works regardless of the working directory it is launched from.
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """All runtime configuration. Values come from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL / PostGIS
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "smart_city_twin"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    # External services (free, no API key required)
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    osrm_base_url: str = "https://router.project-osrm.org"

    # Study area: Islamabad urban area and immediate peri-urban surroundings.
    # Kept deliberately compact so public Overpass and routing services remain usable.
    study_area_west: float = 72.80
    study_area_south: float = 33.60
    study_area_east: float = 73.25
    study_area_north: float = 33.82

    # CRS
    storage_srid: int = 4326   # WGS 84 (storage & web delivery)
    analysis_srid: int = 32643  # WGS 84 / UTM zone 43N (metric analysis)

    @property
    def database_dsn(self) -> str:
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
