from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_provider: str = Field(default="zai", alias="AI_PROVIDER")
    ai_model: str = Field(default="glm-5.1", alias="AI_MODEL")

    opencodego_api_key: str = Field(default="", alias="OPENCODEGO_API_KEY")
    opencodego_api_base_url: str = Field(
        default="https://opencode.ai/zen/go/v1",
        alias="OPENCODEGO_API_BASE_URL",
    )
    opencodego_model: str = Field(default="deepseek-v4-pro", alias="OPENCODEGO_MODEL")

    zai_api_key: str = Field(default="", alias="ZAI_API_KEY")
    zai_api_base_url: str = Field(
        default="https://api.z.ai/api/coding/paas/v4",
        alias="ZAI_API_BASE_URL",
    )
    zai_model: str = Field(default="glm-5.1", alias="ZAI_MODEL")
    github_app_id: str = Field(default="", alias="GITHUB_APP_ID")
    github_app_private_key: str = Field(default="", alias="GITHUB_APP_PRIVATE_KEY")
    github_app_private_key_path: str = Field(default="", alias="GITHUB_APP_PRIVATE_KEY_PATH")
    github_webhook_secret: str = Field(default="", alias="GITHUB_WEBHOOK_SECRET")
    worker_auth_token: str = Field(default="", alias="IDEAREFINERY_WORKER_AUTH_TOKEN")
    worker_claim_timeout_seconds: int = Field(default=900, alias="IDEAREFINERY_WORKER_CLAIM_TIMEOUT_SECONDS")
    worker_max_retries: int = Field(default=3, alias="IDEAREFINERY_WORKER_MAX_RETRIES")
    worker_command_queue_url: str = Field(default="", alias="IDEAREFINERY_WORKER_COMMAND_QUEUE_URL")
    worker_event_queue_url: str = Field(default="", alias="IDEAREFINERY_WORKER_EVENT_QUEUE_URL")
    worker_client_role_arn: str = Field(default="", alias="IDEAREFINERY_WORKER_CLIENT_ROLE_ARN")
    worker_credential_ttl_seconds: int = Field(default=3600, alias="IDEAREFINERY_WORKER_CREDENTIAL_TTL_SECONDS")
    worker_sqs_region: str = Field(default="us-east-1", alias="IDEAREFINERY_WORKER_SQS_REGION")
    max_repair_attempts_per_task: int = Field(default=3, alias="IDEAREFINERY_MAX_REPAIR_ATTEMPTS_PER_TASK")
    max_repair_attempts_per_batch: int = Field(default=5, alias="IDEAREFINERY_MAX_REPAIR_ATTEMPTS_PER_BATCH")
    claude_settings_path: str = Field(
        default=str(Path.home() / ".claude" / "settings.json"),
        alias="CLAUDE_SETTINGS_PATH",
    )


settings = Settings()
