import os

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int

    SECRET_KEY: str
    DATABASE_URL: str
    GEMINI_API_KEY: str

    GEMINI_MODEL: str ="gemini-2.5-flash-lite"

    OLLAMA_BASE_URL :str
    OLLAMA_MODEL : str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    model_config = SettingsConfigDict(env_file=".env",extra="ignore",env_ignore_empty=True)

settings = Settings()