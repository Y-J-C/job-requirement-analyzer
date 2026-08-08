from functools import lru_cache
from typing import Self
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://job_analyzer:job_analyzer_local@localhost:5432/job_analyzer"
    )
    web_origin: str = "http://localhost:3000"
    s3_endpoint_url: str = "http://localhost:19000"
    s3_bucket: str = Field(default="job-source-files", min_length=1, max_length=63)
    s3_region: str = Field(default="us-east-1", min_length=1, max_length=64)
    s3_access_key: str = Field(default="job_analyzer", min_length=1)
    s3_secret_key: SecretStr = SecretStr("job_analyzer_local")
    upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    pdf_max_pages: int = Field(default=50, ge=1, le=500)
    extracted_text_max_chars: int = Field(default=100_000, ge=1_000, le=100_000)
    document_worker_lease_seconds: int = Field(default=120, ge=30, le=3600)
    document_worker_max_attempts: int = Field(default=3, ge=1, le=10)
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_max_tokens: int = Field(default=2000, ge=256, le=8192)
    deepseek_timeout_seconds: float = Field(default=60, ge=5, le=120)
    deepseek_max_output_retries: int = Field(default=1, ge=0, le=2)
    deepseek_max_input_chars: int = Field(default=30_000, ge=1_000, le=100_000)
    analysis_worker_poll_seconds: float = Field(default=1, ge=0.1, le=60)
    analysis_worker_lease_seconds: int = Field(default=600, ge=30, le=3600)
    analysis_worker_max_attempts: int = Field(default=3, ge=1, le=10)
    analysis_worker_retry_delay_seconds: int = Field(default=5, ge=0, le=3600)

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

    @field_validator("s3_endpoint_url")
    @classmethod
    def validate_s3_endpoint_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("S3 endpoint URL must use HTTP or HTTPS")
        return normalized

    @field_validator("s3_bucket", "s3_region", "s3_access_key")
    @classmethod
    def reject_blank_storage_settings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must contain at least 1 character")
        return normalized

    @field_validator("deepseek_model")
    @classmethod
    def validate_deepseek_model(cls, value: str) -> str:
        if value not in {"deepseek-v4-flash", "deepseek-v4-pro"}:
            raise ValueError("DeepSeek model must be a supported V4 model")
        return value

    @model_validator(mode="after")
    def validate_worker_lease_covers_provider_attempts(self) -> Self:
        worst_case_seconds = self.deepseek_timeout_seconds * (
            self.deepseek_max_output_retries + 1
        )
        if self.analysis_worker_lease_seconds <= worst_case_seconds + 30:
            raise ValueError("Analysis worker lease must cover all provider attempts")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
