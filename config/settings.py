"""
RFP Intelligence - Configuration Management

Central configuration using Pydantic settings with multi-provider LLM support.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Provider Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider to use"
    )
    
    # Provider API Keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(default=None, description="Google API key")
    
    # Model Configuration
    llm_model: Optional[str] = Field(
        default=None,
        description="Model to use (defaults based on provider)"
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Model temperature"
    )
    
    # n8n Configuration
    n8n_webhook_url: Optional[str] = Field(
        default=None,
        description="n8n webhook URL for workflow triggers"
    )
    
    # Storage Configuration
    data_dir: Path = Field(
        default=Path("./data"),
        description="Data directory for storage"
    )
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_env: str = Field(default="development", description="API environment")
    cors_origins: str = Field(
        default="http://localhost:8501,http://localhost:3000",
        description="CORS origins (comma-separated)"
    )
    
    # Database Configuration (Neon PostgreSQL)
    database_url: str = Field(
        default="postgresql+asyncpg://localhost/rfp_intelligence",
        description="Database connection URL"
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries for debugging"
    )
    
    # Redis Configuration (Job Queue)
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # JWT Configuration
    jwt_secret: str = Field(
        default="change-this-in-production-use-long-random-string",
        description="JWT signing secret"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=30, description="Access token expiry")
    jwt_refresh_expire_days: int = Field(default=7, description="Refresh token expiry")
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def active_api_key(self) -> Optional[str]:
        """Get the API key for the active provider."""
        key_map = {
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.ANTHROPIC: self.anthropic_api_key,
            LLMProvider.GEMINI: self.google_api_key,
        }
        return key_map.get(self.llm_provider)
    
    @property
    def default_model(self) -> str:
        """Get the default model for the active provider."""
        if self.llm_model:
            return self.llm_model
        
        defaults = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
            LLMProvider.GEMINI: "gemini-1.5-pro",
        }
        return defaults.get(self.llm_provider, "gpt-4o-mini")
    
    # Data directories
    @property
    def rfps_dir(self) -> Path:
        """Directory for stored RFP documents."""
        path = self.data_dir / "rfps"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def outputs_dir(self) -> Path:
        """Directory for agent outputs."""
        path = self.data_dir / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def exports_dir(self) -> Path:
        """Directory for exported documents."""
        path = self.data_dir / "exports"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def knowledge_base_dir(self) -> Path:
        """Directory for knowledge base files."""
        path = self.data_dir / "knowledge_base"
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()
