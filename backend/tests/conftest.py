import pytest

from app.services.radar_link import stop_radar
from app.state import get_state


@pytest.fixture(autouse=True)
def isolate_state(monkeypatch, tmp_path):
    monkeypatch.setenv("RUBBLEECHO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NEBIUS_MODEL_ID", raising=False)
    monkeypatch.delenv("OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("RUBBLEECHO_AI_LIVE", raising=False)
    monkeypatch.delenv("AI_ENABLED", raising=False)
    monkeypatch.delenv("RUBBLEECHO_PROBE_CAMERAS", raising=False)
    stop_radar()
    get_state().reset()
    yield
    stop_radar()
    get_state().reset()


@pytest.fixture
def operator_token(monkeypatch) -> str:
    monkeypatch.setenv("OPERATOR_TOKEN", "test-token")
    return "test-token"


@pytest.fixture
def auth_header(operator_token: str) -> dict[str, str]:
    return {"X-Operator-Token": operator_token}
