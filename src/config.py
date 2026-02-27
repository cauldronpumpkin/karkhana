"""Configuration module for the Software Factory."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class LMStudioConfig(BaseSettings):
    """LM Studio API configuration."""

    model_config = SettingsConfigDict(env_prefix="LM_STUDIO_")

    base_url: str = "http://localhost:1234/v1"
    model_name: str = "qwen-3-coder-next"
    max_tokens: int = 8192
    temperature_creative: float = Field(0.7, ge=0.0, le=1.0)
    temperature_coding: float = Field(0.2, ge=0.0, le=1.0)
    timeout: int = Field(300, gt=0)


class SandboxConfig(BaseSettings):
    """Sandbox execution configuration."""

    model_config = SettingsConfigDict(env_prefix="SANDBOX_")

    timeout: int = Field(120, gt=0)
    max_retries_per_file: int = Field(3, ge=1, le=10)


class AppConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict()

    lm_studio: LMStudioConfig = Field(default_factory=LMStudioConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)


config = AppConfig()
