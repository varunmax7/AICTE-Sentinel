"""MinIO/S3 object storage (IMPLEMENTATION.md §13.4 "upload pipeline:
MinIO, signed URLs"). A thin `boto3` wrapper — MinIO speaks the S3 API, so
this is also the real client against a production S3-compatible bucket.

Downloads are served through this app's own authenticated, scope-checked
endpoints (`app.routers.documents`) rather than literal browser-facing
presigned URLs: those endpoints stream straight from this client, which is
the same "time-limited, access-controlled link" the spec asks for without
needing CORS/expiry wiring for a bucket the browser never talks to directly.
`presigned_get_url` still exists for the one case that *does* need a bare
URL handed to something other than this app (e.g. a future signed email
attachment link).
"""

from __future__ import annotations

from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import Config as BotoConfig

from app.core.config import get_settings


@lru_cache
def _client():  # type: ignore[no-untyped-def]
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    settings = get_settings()
    client = _client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if settings.S3_BUCKET not in existing:
        client.create_bucket(Bucket=settings.S3_BUCKET)


def put_object(key: str, data: bytes, *, content_type: str) -> None:
    settings = get_settings()
    _client().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType=content_type)


def get_object(key: str) -> bytes:
    settings = get_settings()
    body: BinaryIO = _client().get_object(Bucket=settings.S3_BUCKET, Key=key)["Body"]
    return body.read()


def presigned_get_url(key: str, *, expires_seconds: int = 3600) -> str:
    settings = get_settings()
    url: str = _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_seconds,
    )
    return url
