"""Storage interface for the worker: local disk by default, S3 as an option.

Mirrors api/app/storage.py; the worker cannot import the API package.
"""
from __future__ import annotations

import pathlib
import shutil

from .config import settings


class LocalStorage:
    def __init__(self, root: str):
        self.root = pathlib.Path(root)

    def _path(self, key: str) -> pathlib.Path:
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"unsafe storage key: {key!r}")
        return path

    def ensure_bucket(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def put_file(self, key: str, path: str) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)

    def get_file(self, key: str, path: str) -> None:
        dest = pathlib.Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._path(key), dest)

    def delete_prefix(self, prefix: str) -> None:
        directory = self._path(prefix)
        if directory.is_dir():
            shutil.rmtree(directory, ignore_errors=True)

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self._path(prefix) if prefix else self.root
        if not base.exists():
            return []
        return sorted(
            str(p.relative_to(self.root)) for p in base.rglob("*") if p.is_file()
        )


class S3Storage:
    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(s3={"addressing_style": "path"}),
        )
        self.client.meta.events.register(
            "before-send", lambda request, **kwargs: request.headers.pop("Expect", None)
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except self.client.exceptions.NoSuchBucket:
            self.client.create_bucket(Bucket=self.bucket)

    def put_file(self, key: str, path: str) -> None:
        self.client.upload_file(path, self.bucket, key)

    def get_file(self, key: str, path: str) -> None:
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, path)

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                self.client.delete_object(Bucket=self.bucket, Key=obj["Key"])

    def list_keys(self, prefix: str = "") -> list[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [o["Key"] for o in page.get("Contents", [])]
        return sorted(keys)


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        if settings.storage_driver == "s3":
            _storage = S3Storage()
        else:
            _storage = LocalStorage(settings.storage_local_dir)
    return _storage


def put_file(key: str, path: str) -> None:
    get_storage().put_file(key, path)


def get_file(key: str, path: str) -> None:
    get_storage().get_file(key, path)


def delete_prefix(prefix: str) -> None:
    get_storage().delete_prefix(prefix)


def list_keys(prefix: str = "") -> list[str]:
    return get_storage().list_keys(prefix)
