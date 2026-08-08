from io import BytesIO
from typing import BinaryIO

from botocore.exceptions import BotoCoreError, ClientError

from app.storage.contracts import StorageUnavailableError


class S3ObjectStore:
    def __init__(self, *, client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise StorageUnavailableError("Object storage is unavailable") from error
            try:
                self._client.create_bucket(Bucket=self._bucket)
            except (BotoCoreError, ClientError) as create_error:
                raise StorageUnavailableError("Object storage is unavailable") from create_error
        except BotoCoreError as error:
            raise StorageUnavailableError("Object storage is unavailable") from error

    def put(self, object_key: str, content: BinaryIO, content_type: str) -> None:
        try:
            self._client.upload_fileobj(
                content,
                self._bucket,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageUnavailableError("Object storage is unavailable") from error

    def read(self, object_key: str) -> bytes:
        target = BytesIO()
        try:
            self._client.download_fileobj(self._bucket, object_key, target)
        except (BotoCoreError, ClientError) as error:
            raise StorageUnavailableError("Object storage is unavailable") from error
        return target.getvalue()

    def delete(self, object_key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=object_key)
        except (BotoCoreError, ClientError) as error:
            raise StorageUnavailableError("Object storage is unavailable") from error
