from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn, Field
from typing import Optional

class Settings(BaseSettings):
    MAIN_DOMAIN: str = "mydummy.local" #"mydummy.local"  # Updated main domain
    APP_NAME: str = "Cilico"
    API_PREFIX: str = ""
    DEBUG: bool = False
    
    # Postgres (Multi-tenant)
    DATABASE_URL: PostgresDsn = "postgresql+asyncpg://postgres:balram7677@localhost/cilico"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 5
    
    # Redis
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    
    # Auth
    JWT_SECRET: str = "super-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Security
    CORS_ORIGINS: list = ["*"]
    TRUSTED_HOSTS: list = ["*.mydummy.local"]  # Updated trusted hosts
    
    # Encryption
    ENCRYPTION_KEY: str = "default-secure-encryption-key"  # Added encryption key
    
        # Razorpay Config
    RAZORPAY_KEY_ID: str = "rzp_test_V4NUSlaghEuXRX"
    RAZORPAY_KEY_SECRET: str = "ihQTMsCgrzplIvQzhG01W7fQ"

    PLANS: dict[str, dict] = Field(default={
        "basic" : {"price": 102.99, "features":["Appont booking", "Telemedicine"]},
        "Pro":{ "price":202.99, "features":["abc","def"]},
        "Advanced":{ "price":302.99,"features":[] }
    })

    class Config:
        env_file = ".env"

settings = Settings()