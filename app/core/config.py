import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    DEBUG: bool = True

    # DATABASE SETTINGS 
    DATABASE_URI: str

    # APPLICATION SETTINGS
    app_name: str = "Liinke B2B"
    admin_email: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
    )

settings = Settings()