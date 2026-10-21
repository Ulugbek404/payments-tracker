import datetime as dt

import pytest


def test_add_and_list_payments_newest_first(client, make_student, pay):
    s = make_student()
    pay(s["id"], 100_000, "2026-09-05")
    pay(s["id"], 250_000, "2026-09-20")
    pay(s["id"], 50_000, "2026-08-31")

    r = client.get(f"/students/{s['id']}/payments")
    assert r.status_code == 200
    assert [(p["date"], p["amount"]) for p in r.json()] == [
        ("2026-09-20", 250_000),
        ("2026-09-05", 100_000),
        ("2026-08-31", 50_000),
    ]


def test_payment_response_shape(client, make_student):
    s = make_student()
    r = client.post("/payments", json={"student_id": s["id"], "amount": 123, "date": "2026-09-05"})
    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert (body["student_id"], body["amount"], body["date"]) == (s["id"], 123, "2026-09-05")


def test_date_defaults_to_today(client, make_student):
    s = make_student()
    r = client.post("/payments", json={"student_id": s["id"], "amount": 1000})
    assert r.status_code == 201
    assert r.json()["date"] == dt.date.today().isoformat()


def test_list_contains_only_this_students_payments(client, make_student, pay):
    a = make_student(name="A")
    b = make_student(name="B")
    pay(a["id"], 1000, "2026-09-05")
    pay(b["id"], 2000, "2026-09-05")

    assert [p["amount"] for p in client.get(f"/students/{a['id']}/payments").json()] == [1000]
    assert [p["amount"] for p in client.get(f"/students/{b['id']}/payments").json()] == [2000]


def test_empty_list_for_student_without_payments(client, make_student):
    s = make_student()
    assert client.get(f"/students/{s['id']}/payments").json() == []


def test_payment_for_unknown_student_is_404(client):
    r = client.post("/payments", json={"student_id": 999, "amount": 1000, "date": "2026-09-05"})
    assert r.status_code == 404


def test_listing_payments_of_unknown_student_is_404(client):
    assert client.get("/students/999/payments").status_code == 404


@pytest.mark.parametrize(
    "override",
    [
        {"amount": 0},
        {"amount": -5},
        {"amount": "abc"},
        {"amount": 10.5},
        {"date": "05.09.2026"},
        {"date": "2026-02-30"},
    ],
)
def test_invalid_payment_is_422(client, make_student, override):
    s = make_student()
    body = {"student_id": s["id"], "amount": 1000, "date": "2026-09-05"} | override
    assert client.post("/payments", json=body).status_code == 422
