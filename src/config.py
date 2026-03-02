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
    max_concurrency: int = Field(1, ge=1, le=16)


class SandboxConfig(BaseSettings):
    """Sandbox execution configuration."""

    model_config = SettingsConfigDict(env_prefix="SANDBOX_")

    timeout: int = Field(120, gt=0)
    max_retries_per_file: int = Field(3, ge=1, le=10)


class AgentCommsConfig(BaseSettings):
    """Inter-agent communications feature flags."""

    model_config = SettingsConfigDict(env_prefix="AGENT_COMMS_")

    enabled: bool = False
    max_rounds: int = Field(8, ge=1, le=64)
    escalate_blocking_only: bool = True


class ToolCallingConfig(BaseSettings):
    """Tool-calling controls for local model compatibility."""

    model_config = SettingsConfigDict(env_prefix="TOOL_CALLING_")

    enabled: bool = True
    fallback_enabled: bool = True
    max_rounds: int = Field(4, ge=1, le=32)
    file_tool_max_chars: int = Field(12000, ge=256, le=200000)


class ReasoningSettings(BaseSettings):
    """Reasoning controls defaults (can be overridden globally/job/launch)."""

    model_config = SettingsConfigDict(env_prefix="REASONING_")

    enabled: bool = False
    profile: str = "balanced"
    architect_tot_paths: int = Field(3, ge=1, le=8)
    architect_tot_parallel: bool = True
    critic_enabled: bool = True
    thinking_modules_enabled: bool = True
    thinking_visibility: str = "logs"
    tdd_enabled: bool = True
    tdd_time_split_percent: int = Field(40, ge=0, le=100)
    tdd_max_iterations: int = Field(5, ge=1, le=20)
    tdd_fail_open: bool = True


class AppConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict()

    lm_studio: LMStudioConfig = Field(default_factory=LMStudioConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    agent_comms: AgentCommsConfig = Field(default_factory=AgentCommsConfig)
    tool_calling: ToolCallingConfig = Field(default_factory=ToolCallingConfig)
    reasoning: ReasoningSettings = Field(default_factory=ReasoningSettings)


config = AppConfig()
