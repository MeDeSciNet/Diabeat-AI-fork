"""Object storage for raw waveforms, derived series and exports.

S3/MinIO when configured, local filesystem otherwise. The interface is
deliberately tiny: everything ING stores is a whole object written once.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Protocol

import numpy as np

from .settings import get_settings


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...


class LocalStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key

    def put(self, key: str, data: bytes) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return f"file://{p}"

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3Store:
    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str) -> None:
        import boto3

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            self.client.create_bucket(Bucket=bucket)

    def put(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return f"s3://{self.bucket}/{key}"

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


_store: ObjectStore | None = None


def get_store() -> ObjectStore:
    global _store
    if _store is None:
        s = get_settings()
        if s.s3_endpoint:
            _store = S3Store(s.s3_endpoint, s.s3_bucket, s.s3_access_key, s.s3_secret_key)
        else:
            _store = LocalStore(s.local_storage_dir)
    return _store


def reset_store() -> None:
    global _store
    _store = None


def save_arrays(key: str, **arrays: np.ndarray) -> str:
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return get_store().put(key, buf.getvalue())


def load_arrays(key: str) -> dict[str, np.ndarray]:
    with np.load(io.BytesIO(get_store().get(key))) as z:
        return {k: z[k] for k in z.files}


def derived_key(session_id: str) -> str:
    return f"sessions/{session_id}/derived.npz"


def raw_key(session_id: str, seq: int) -> str:
    return f"sessions/{session_id}/raw/chunk_{seq:06d}.npz"
