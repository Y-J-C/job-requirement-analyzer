from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://job_analyzer:job_analyzer_local@localhost:5432/job_analyzer"
    )
    web_origin: str = "http://localhost:3000"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_max_tokens: int = Field(default=2000, ge=256, le=8192)
    deepseek_timeout_seconds: float = Field(default=60, ge=5, le=120)
    deepseek_max_output_retries: int = Field(default=1, ge=0, le=2)
    deepseek_max_input_chars: int = Field(default=30_000, ge=1_000, le=100_000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("deepseek_base_url")
    @classmethod
    def validate_deepseek_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.deepseek.com"
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/v1"}
        ):
            raise ValueError("DeepSeek base URL must be the official HTTPS API endpoint")
        return normalized

    @field_validator("deepseek_model")
    @classmethod
    def validate_deepseek_model(cls, value: str) -> str:
        if value not in {"deepseek-v4-flash", "deepseek-v4-pro"}:
            raise ValueError("DeepSeek model must be a supported V4 model")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
