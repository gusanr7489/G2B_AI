from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://g2b_user:g2b_pass@localhost:5432/g2b_ai"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # 나라장터 API
    g2b_api_key: str = ""

    # 리브레AI API
    libreai_api_key: str = ""
    libreai_api_url: str = "https://convert.liberoai.net/api"

    # Google Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-pro-preview"
    gemini_fallback_model: str = "gemini-2.5-pro"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
