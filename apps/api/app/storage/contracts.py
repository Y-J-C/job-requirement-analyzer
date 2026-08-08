from typing import BinaryIO, Protocol


class StorageUnavailableError(RuntimeError):
    """Raised when object storage cannot complete an operation."""


class ObjectStore(Protocol):
    def ensure_bucket(self) -> None: ...

    def put(self, object_key: str, content: BinaryIO, content_type: str) -> None: ...

    def read(self, object_key: str) -> bytes: ...

    def delete(self, object_key: str) -> None: ...
