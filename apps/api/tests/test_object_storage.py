from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from app.storage.contracts import StorageUnavailableError
from app.storage.s3 import S3ObjectStore


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.bucket_exists = False
        self.fail = False

    def head_bucket(self, **_kwargs) -> None:
        if not self.bucket_exists:
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "HeadBucket")

    def create_bucket(self, **_kwargs) -> None:
        self.bucket_exists = True

    def upload_fileobj(self, content, _bucket, key, ExtraArgs) -> None:
        if self.fail:
            raise ClientError({"Error": {"Code": "500", "Message": "secret"}}, "PutObject")
        assert ExtraArgs == {"ContentType": "text/markdown"}
        self.objects[key] = content.read()

    def download_fileobj(self, _bucket, key, target) -> None:
        if self.fail:
            raise ClientError({"Error": {"Code": "500", "Message": "secret"}}, "GetObject")
        target.write(self.objects[key])

    def delete_object(self, Bucket, Key) -> None:
        if self.fail:
            raise ClientError({"Error": {"Code": "500", "Message": "secret"}}, "DeleteObject")
        self.objects.pop(Key, None)


def test_s3_store_uploads_reads_and_deletes_object() -> None:
    client = FakeS3Client()
    store = S3ObjectStore(client=client, bucket="documents")

    store.ensure_bucket()
    store.put("source/random-id", BytesIO(b"hello"), "text/markdown")

    assert store.read("source/random-id") == b"hello"
    store.delete("source/random-id")
    assert client.objects == {}


def test_s3_store_maps_sdk_errors_without_leaking_details() -> None:
    client = FakeS3Client()
    client.bucket_exists = True
    client.fail = True
    store = S3ObjectStore(client=client, bucket="documents")

    with pytest.raises(StorageUnavailableError, match="Object storage is unavailable"):
        store.put("source/random-id", BytesIO(b"hello"), "text/markdown")
