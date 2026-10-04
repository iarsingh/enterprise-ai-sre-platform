from fastapi.testclient import TestClient
from entsre.main import app

client = TestClient(app)


def test_runs_and_refuses_a_write():
    payload = client.post("/agent/run", json={"goal": 'slo check', **{'payload': {'burn': 4}}}).json()
    assert payload["refused"] is False
    assert payload["applied"] is False
    assert payload["recommend"] == "freeze"
    refused = client.post("/agent/run", json={"goal": 'disable slo'}).json()
    assert refused["refused"] is True
