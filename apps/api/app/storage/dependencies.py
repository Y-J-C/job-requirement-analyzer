from functools import lru_cache

import boto3
from botocore.config import Config

from app.core.config import get_settings
from app.storage.s3 import S3ObjectStore


@lru_cache
def get_object_store() -> S3ObjectStore:
    settings = get_settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    return S3ObjectStore(client=client, bucket=settings.s3_bucket)
