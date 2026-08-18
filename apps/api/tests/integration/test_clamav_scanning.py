import os

import pytest

from app.core.config import Settings
from app.security.malware import ClamAvFileScanner, MalwareDetectedError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_MALWARE_TESTS") != "1",
        reason="set RUN_MALWARE_TESTS=1 with the local ClamAV service running",
    ),
]

EICAR_TEST_FILE = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


def build_scanner() -> ClamAvFileScanner:
    settings = Settings()
    return ClamAvFileScanner(
        host=settings.clamav_host,
        port=settings.clamav_port,
        timeout=settings.clamav_timeout_seconds,
    )


def test_clamav_accepts_clean_content() -> None:
    build_scanner().scan("普通岗位描述：要求熟练使用 SQL".encode())


def test_clamav_detects_the_standard_eicar_test_file() -> None:
    with pytest.raises(MalwareDetectedError):
        build_scanner().scan(EICAR_TEST_FILE)
