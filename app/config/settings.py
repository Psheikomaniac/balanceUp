from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, SecretStr
from typing import Optional
import os
from functools import lru_cache
import secrets
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class Settings(BaseSettings):
    # API settings
    PROJECT_NAME: str = "Balance Up API"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8000, gt=0)
    API_V1_STR: str = "/api/v1"
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///database/penalties.db",
        description="Database connection string. For SQLite, use sqlite:///path/to/database.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    
    # Security settings
    SECRET_KEY: SecretStr = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for signing tokens. Must be kept secret in production."
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    
    # Rate limiting
    RATE_LIMIT_WINDOW: int = Field(default=60, gt=0)
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=10, gt=0)
    
    # Logging settings
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="Path to log file. If not set, logs to stdout"
    )
    
    # File import settings
    IMPORT_DIRECTORY: str = Field(
        default="app/cashbox",
        description="Directory where import files are stored"
    )
    ARCHIVE_DIRECTORY: str = Field(
        default="app/cashbox/archive",
        description="Directory where processed import files are archived"
    )

    @field_validator("PORT", "RATE_LIMIT_MAX_REQUESTS", "RATE_LIMIT_WINDOW", "ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_positive_numbers(cls, v: int, info):
        if v <= 0:
            raise ValueError(f"{info.field_name} must be greater than 0")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str):
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(allowed_levels)}")
        return v.upper()

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str):
        allowed_formats = ["json", "text"]
        if v.lower() not in allowed_formats:
            raise ValueError(f"LOG_FORMAT must be one of: {', '.join(allowed_formats)}")
        return v.lower()
    
    # Environment-specific configuration properties
    @property
    def is_development(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @property
    def is_production(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @property
    def is_test(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "test"
    
    # Get the SECRET_KEY as a string
    def get_secret_key(self) -> str:
        return self.SECRET_KEY.get_secret_value()
    
    # Model configuration with support for .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

# Cache settings to avoid reloading configuration on every request
@lru_cache
def get_settings() -> Settings:
    """Get application settings with caching for better performance"""
    return Settings()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///database/penalties.db")
    API_KEY: str = os.getenv("API_KEY", "default_api_key")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

settings = Settings()
