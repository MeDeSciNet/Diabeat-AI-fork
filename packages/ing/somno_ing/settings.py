"""Runtime configuration.

Everything is environment-driven so the same image runs under docker compose,
in CI, and in a bare pytest process with no broker or database.

Values are read when ``get_settings()`` is first called, not at import time.
That distinction matters: field defaults evaluated at class-definition time are
frozen the moment the module is imported, which silently ignores anything the
process sets afterwards - a test harness configuring a temporary database, or an
entrypoint script exporting credentials before starting the app.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = PACKAGE_DIR / "config"

TRUTHY = ("1", "true", "yes", "on")


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in TRUTHY


class Settings(BaseModel):
    database_url: str
    redis_url: str
    mqtt_url: str

    # Object storage. Falls back to the local filesystem when no S3 endpoint is
    # configured, which is what tests and `make demo` use.
    s3_endpoint: str | None
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    local_storage_dir: Path

    # PRD 10.2: raw waveform retention is short and configurable; derived series
    # and analysis results live longer.
    raw_retention_days: int
    store_raw: bool

    detector_config: Path
    risk_config: Path
    alert_rules: Path

    celery_eager: bool
    api_auth_required: bool
    dev_api_token: str
    pam_base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/somno.db"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            mqtt_url=os.getenv("MQTT_URL", "mqtt://localhost:1883"),
            s3_endpoint=os.getenv("S3_ENDPOINT") or None,
            s3_bucket=os.getenv("S3_BUCKET", "somno"),
            s3_access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            s3_secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            local_storage_dir=Path(os.getenv("LOCAL_STORAGE_DIR", "./data/objects")),
            raw_retention_days=int(os.getenv("RAW_RETENTION_DAYS", "90")),
            store_raw=_flag("STORE_RAW"),
            detector_config=Path(os.getenv("DETECTOR_CONFIG", CONFIG_DIR / "detector.yaml")),
            risk_config=Path(os.getenv("RISK_CONFIG", CONFIG_DIR / "risk.yaml")),
            alert_rules=Path(os.getenv("ALERT_RULES", CONFIG_DIR / "alert_rules.yaml")),
            celery_eager=_flag("CELERY_TASK_ALWAYS_EAGER"),
            api_auth_required=_flag("API_AUTH_REQUIRED", default=True),
            dev_api_token=os.getenv("DEV_API_TOKEN", "dev-token"),
            pam_base_url=os.getenv("PAM_BASE_URL", "http://localhost:8100"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
