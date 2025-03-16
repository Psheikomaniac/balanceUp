from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional
import os

class Settings(BaseSettings):
    # API settings
    PROJECT_NAME: str = "Balance Up API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = Field(default=8000, gt=0)
    API_V1_STR: str = "/api/v1"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///database/penalties.db"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    
    # Security settings
    SECRET_KEY: str = Field(default="development_secret_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Rate limiting
    RATE_LIMIT_WINDOW: int = Field(default=60, gt=0)
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=10, gt=0)
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # File import settings
    IMPORT_DIRECTORY: str = "app/cashbox"
    ARCHIVE_DIRECTORY: str = "app/cashbox/archive"

    @field_validator("PORT", "RATE_LIMIT_MAX_REQUESTS", "RATE_LIMIT_WINDOW", "ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_positive_numbers(cls, v: int, info):
        if v <= 0:
            raise ValueError(f"{info.field_name} must be greater than 0")
        return v

    # Environment-specific configuration
    @property
    def is_development(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @property
    def is_production(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
