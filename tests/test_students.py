import sqlite3

import pytest

from app.db import db_path


def test_create_and_get(client, make_student):
    s = make_student(name="Алишер", fee=450_000)
    assert s["id"] > 0
    assert (s["name"], s["group"], s["monthly_fee"]) == ("Алишер", "English A1", 450_000)

    r = client.get(f"/students/{s['id']}")
    assert r.status_code == 200
    assert r.json() == s


def test_list(client, make_student):
    assert client.get("/students").json() == []
    a = make_student(name="A")
    b = make_student(name="B")
    assert [s["id"] for s in client.get("/students").json()] == [a["id"], b["id"]]


def test_update(client, make_student):
    s = make_student()
    r = client.put(
        f"/students/{s['id']}",
        json={"name": "Новое имя", "phone": "+7 999 123-45-67", "group": "IELTS", "monthly_fee": 700_000},
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["id"], body["name"], body["group"], body["monthly_fee"]) == (s["id"], "Новое имя", "IELTS", 700_000)
    assert client.get(f"/students/{s['id']}").json() == body


def test_delete(client, make_student):
    s = make_student()
    assert client.delete(f"/students/{s['id']}").status_code == 204
    assert client.get(f"/students/{s['id']}").status_code == 404
    assert client.get("/students").json() == []


def test_delete_removes_students_payments(client, make_student, pay):
    s = make_student()
    other = make_student(name="Другой")
    pay(s["id"], 100_000, "2026-09-05")
    pay(other["id"], 100_000, "2026-09-05")

    client.delete(f"/students/{s['id']}")

    conn = sqlite3.connect(db_path())
    rows = conn.execute("SELECT student_id FROM payments").fetchall()
    conn.close()
    assert rows == [(other["id"],)]


@pytest.mark.parametrize("method", ["get", "delete"])
def test_unknown_student_is_404(client, method):
    assert getattr(client, method)("/students/999").status_code == 404


def test_update_unknown_student_is_404(client):
    body = {"name": "X", "phone": "+998901234567", "group": "G", "monthly_fee": 1}
    assert client.put("/students/999", json=body).status_code == 404


@pytest.mark.parametrize(
    "override",
    [
        {"name": ""},
        {"name": "   "},
        {"phone": "abc"},
        {"phone": "123"},
        {"group": ""},
        {"monthly_fee": 0},
        {"monthly_fee": -100},
        {"monthly_fee": "много"},
    ],
)
def test_invalid_student_is_422(client, override):
    body = {"name": "Алишер", "phone": "+998901234567", "group": "G1", "monthly_fee": 500_000} | override
    assert client.post("/students", json=body).status_code == 422


def test_missing_field_is_422(client):
    assert client.post("/students", json={"name": "Алишер"}).status_code == 422
