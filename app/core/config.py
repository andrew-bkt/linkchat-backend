# backend/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    OPENAI_API_KEY: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS origins
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()