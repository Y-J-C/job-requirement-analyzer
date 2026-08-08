import os
import uuid
from io import BytesIO

import pytest

from app.storage.dependencies import get_object_store

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_STORAGE_TESTS") != "1",
        reason="set RUN_STORAGE_TESTS=1 with MinIO running",
    ),
]


def test_minio_round_trip() -> None:
    store = get_object_store()
    object_key = f"integration/{uuid.uuid4().hex}"
    store.ensure_bucket()
    try:
        store.put(object_key, BytesIO(b"integration-check"), "text/plain")
        assert store.read(object_key) == b"integration-check"
    finally:
        store.delete(object_key)
