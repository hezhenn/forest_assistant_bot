from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_bot_token: str
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    forest_archive_path: Path = Path("./forest_archive")
    db_path: Path = Path("./data/forest_bot.db")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()