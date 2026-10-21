import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client backed by a fresh, empty SQLite file for every test."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:  # the `with` block runs the startup hook (creates tables)
        yield c


@pytest.fixture
def make_student(client):
    def _make(name="Алишер", fee=500_000, group="English A1", phone="+998 90 123 45 67"):
        r = client.post(
            "/students",
            json={"name": name, "phone": phone, "group": group, "monthly_fee": fee},
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest.fixture
def pay(client):
    def _pay(student_id, amount, date):
        r = client.post("/payments", json={"student_id": student_id, "amount": amount, "date": date})
        assert r.status_code == 201, r.text
        return r.json()

    return _pay
