from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # LLM Settings
    LLM_PROVIDER: str = "openai" # openai, anthropic, deepseek
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    
    # AWS Settings
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/asoc"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector DB
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    
    # Security
    OPA_URL: str = "http://localhost:8181"
    VAULT_ADDR: str = "http://localhost:8200"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
