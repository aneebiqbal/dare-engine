"""S3-compatible storage (worker side)."""
from __future__ import annotations

import boto3
from botocore.config import Config

from .config import settings


def _strip_expect(request, **kwargs):
    request.headers.pop("Expect", None)


def _client():
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(s3={"addressing_style": "path"}),
    )
    client.meta.events.register("before-send", _strip_expect)
    return client


def put_file(key: str, path: str) -> None:
    _client().upload_file(path, settings.s3_bucket, key)


def get_file(key: str, path: str) -> None:
    _client().download_file(settings.s3_bucket, key, path)
