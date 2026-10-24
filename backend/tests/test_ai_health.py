from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthcheck_does_not_call_out_when_unconfigured(operator_token, auth_header) -> None:
    response = client.post("/api/ai/healthcheck", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NOT_CONFIGURED"
    assert body["live_call"] is False
    assert body["nvidia_online"] is False
    assert operator_token not in str(body)
