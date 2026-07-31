import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolated_backend(tmp_path_factory):
    """Every run gets a fresh SQLite file and object store.

    The service is written so that neither Postgres, MinIO, Redis nor a broker
    is required to exercise it; this fixture is what makes that true in practice.
    """
    root = tmp_path_factory.mktemp("somno")
    os.environ["DATABASE_URL"] = f"sqlite:///{root}/somno.db"
    os.environ["LOCAL_STORAGE_DIR"] = str(root / "objects")
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
    os.environ["API_AUTH_REQUIRED"] = "false"
    os.environ.pop("S3_ENDPOINT", None)

    from somno_ing.db import init_db, reset_engine
    from somno_ing.storage import reset_store

    reset_engine()
    reset_store()
    init_db()
    yield
    reset_engine()
    reset_store()


@pytest.fixture(scope="session")
def analysed_session():
    """One short healthy night, run end to end. Shared - it is the slow part."""
    from somno_ing.devtools import run_scenario

    return run_scenario(
        scenario="healthy_adult",
        seed=42,
        duration_min=90.0,
        subject_code="SUBJ-TEST",
        bed_id="BED-TEST",
        device_id="dev-shared",
    )
