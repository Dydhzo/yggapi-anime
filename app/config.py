from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Base de données
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "password")
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "yggapi_anime")
    
    # YGG API
    ygg_api_base_url: str = os.getenv("YGG_API_BASE_URL", "https://yggapi.eu")
    api_delay_seconds: int = int(os.getenv("API_DELAY_SECONDS", "1"))
    
    # Scheduler
    update_interval_seconds: int = int(os.getenv("UPDATE_INTERVAL_SECONDS", "3600"))
    
    # Catégories
    anime_series_category: int = int(os.getenv("ANIME_SERIES_CATEGORY", "2179"))
    anime_film_category: int = int(os.getenv("ANIME_FILM_CATEGORY", "2178"))
    
    # Pagination
    items_per_page: int = int(os.getenv("ITEMS_PER_PAGE", "100"))
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"

settings = Settings()