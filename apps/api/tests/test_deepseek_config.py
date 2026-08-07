import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("model", ["deepseek-v4-flash", "deepseek-v4-pro"])
def test_settings_accept_current_deepseek_v4_models(model: str) -> None:
    settings = Settings(_env_file=None, deepseek_model=model)

    assert settings.deepseek_model == model


def test_settings_rejects_retired_deepseek_chat_alias() -> None:
    with pytest.raises(ValidationError, match="supported V4 model"):
        Settings(_env_file=None, deepseek_model="deepseek-chat")


def test_settings_rejects_worker_lease_shorter_than_provider_worst_case() -> None:
    with pytest.raises(ValidationError, match="lease must cover"):
        Settings(
            _env_file=None,
            deepseek_timeout_seconds=60,
            deepseek_max_output_retries=1,
            analysis_worker_lease_seconds=120,
        )
