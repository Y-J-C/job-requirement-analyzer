import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_valid_local_s3_configuration() -> None:
    settings = Settings(
        _env_file=None,
        s3_endpoint_url="http://localhost:19000",
        s3_bucket="job-source-files",
        upload_max_bytes=10 * 1024 * 1024,
        pdf_max_pages=50,
        extracted_text_max_chars=100_000,
    )

    assert settings.s3_endpoint_url == "http://localhost:19000"
    assert settings.s3_bucket == "job-source-files"
    assert settings.image_max_files == 10
    assert settings.image_total_max_bytes == 50 * 1024 * 1024
    assert settings.image_max_pixels == 40_000_000
    assert settings.image_total_max_pixels == 120_000_000


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("s3_endpoint_url", "ftp://localhost:19000", "HTTP or HTTPS"),
        ("s3_bucket", "   ", "at least 1 character"),
        ("upload_max_bytes", 0, "greater than or equal to 1"),
        ("pdf_max_pages", 0, "greater than or equal to 1"),
        ("extracted_text_max_chars", 100_001, "less than or equal to 100000"),
        ("image_max_files", 0, "greater than or equal to 1"),
        ("image_max_pixels", 0, "greater than or equal to 1"),
        ("image_total_max_pixels", 0, "greater than or equal to 1"),
    ],
)
def test_settings_reject_invalid_storage_limits(field: str, value: object, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None, **{field: value})
