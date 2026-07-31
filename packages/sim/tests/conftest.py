import pytest

from somno_sim.config import load_scenario


@pytest.fixture
def short():
    """A short scenario keeps the suite fast without changing any behaviour."""

    def _make(name: str = "healthy_adult", minutes: float = 30.0):
        return load_scenario(name).model_copy(update={"duration_min": minutes})

    return _make
