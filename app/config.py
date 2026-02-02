"""Configuration management using Pydantic Settings."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields
    )
    
    # Database (REQUIRED - no default for security)
    DATABASE_URL: str
    
    # Database Pool Settings (Optimized for production)
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30
    
    # Redis (for Huey task queue in production)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Google Gemini API (FREE tier)
    GOOGLE_API_KEY: str
    GOOGLE_MODEL: str = "gemini-2.5-flash"
    
    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False  # Default False for security; enable explicitly in dev
    
    # Huey Worker Settings
    HUEY_WORKERS: int = 2
    HUEY_INITIAL_DELAY: int = 100  # milliseconds
    
    # API Settings
    API_TIMEOUT_SECONDS: int = 30  # External API call timeout
    
    # Rate Limiting (requests per minute per IP)
    RATE_LIMIT_PER_MINUTE: int = 30  # Conservative to protect Gemini quota (60/min)


settings = Settings()


def get_cors_origins_list() -> list[str]:
    """Parse CORS_ORIGINS string into list."""
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

