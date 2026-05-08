from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "LLM Local Test Lab"
    app_host: str = "0.0.0.0"
    app_port: int = 7357
    app_debug: bool = True
    database_url: str = "sqlite:///data/app.db"
    config_path: str = "config/config.yaml"
    uploads_dir: str = "app/uploads"
    reports_dir: str = "data/reports"
    exports_dir: str = "data/exports"
    secrets_file: str = "secrets/secret.key"
    max_upload_mb: int = 50

    allowed_extensions: set[str] = {
        ".txt", ".md", ".json", ".csv", ".pdf", ".png", ".jpg", ".jpeg"
    }

    model_config = {"env_prefix": "LLM_"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
