"""MinIO storage helpers for user avatars."""

from io import BytesIO
from uuid import uuid4

import boto3
from botocore.client import Config

from app.core.config import settings


def upload_avatar(content: bytes, content_type: str) -> str:
    """Store an avatar in MinIO and return its object key."""
    client = boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.minio_secure else 'http'}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
    )
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.minio_bucket)

    key = f"avatars/{uuid4()}"
    client.put_object(Bucket=settings.minio_bucket, Key=key, Body=BytesIO(content), ContentType=content_type)
    return key
