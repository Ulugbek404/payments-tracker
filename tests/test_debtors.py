import datetime as dt

import pytest

SEPT = "2026-09"


def debtors(client, month=SEPT):
    r = client.get("/debtors", params={"month": month})
    assert r.status_code == 200, r.text
    return r.json()


def test_student_without_payments_owes_full_fee(client, make_student):
    s = make_student(fee=500_000)
    body = debtors(client)
    assert body["month"] == SEPT
    assert body["count"] == 1
    assert body["debtors"][0] == {
        "student_id": s["id"],
        "name": s["name"],
        "phone": s["phone"],
        "group": s["group"],
        "monthly_fee": 500_000,
        "paid": 0,
        "debt": 500_000,
    }


def test_partial_payment_reduces_debt(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 200_000, "2026-09-10")
    d = debtors(client)["debtors"][0]
    assert (d["paid"], d["debt"]) == (200_000, 300_000)


def test_payments_within_month_are_summed(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 100_000, "2026-09-01")
    pay(s["id"], 150_000, "2026-09-15")
    pay(s["id"], 50_000, "2026-09-30")
    d = debtors(client)["debtors"][0]
    assert (d["paid"], d["debt"]) == (300_000, 200_000)


def test_fully_paid_is_not_a_debtor(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 500_000, "2026-09-10")
    body = debtors(client)
    assert body["debtors"] == []
    assert (body["count"], body["total_debt"]) == (0, 0)


def test_paid_in_installments_to_the_full_fee_is_not_a_debtor(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 300_000, "2026-09-02")
    pay(s["id"], 200_000, "2026-09-25")
    assert debtors(client)["debtors"] == []


def test_overpaid_is_not_a_debtor(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 800_000, "2026-09-10")
    assert debtors(client)["debtors"] == []


def test_only_payments_of_the_requested_month_count(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 111, "2026-08-31")  # last day of the previous month -> not counted
    pay(s["id"], 222, "2026-09-01")  # first day -> counted
    pay(s["id"], 333, "2026-09-30")  # last day -> counted
    pay(s["id"], 444, "2026-10-01")  # first day of the next month -> not counted
    d = debtors(client)["debtors"][0]
    assert (d["paid"], d["debt"]) == (555, 500_000 - 555)


def test_other_month_has_its_own_debt(client, make_student, pay):
    s = make_student(fee=500_000)
    pay(s["id"], 500_000, "2026-09-10")
    assert debtors(client, "2026-09")["debtors"] == []
    assert debtors(client, "2026-10")["debtors"][0]["debt"] == 500_000


def test_december_boundary(client, make_student, pay):
    s = make_student(fee=1000)
    pay(s["id"], 100, "2026-12-31")  # counted for December
    pay(s["id"], 900, "2027-01-01")  # belongs to January
    d = debtors(client, "2026-12")["debtors"][0]
    assert (d["paid"], d["debt"]) == (100, 900)


def test_students_are_not_mixed_up(client, make_student, pay):
    a = make_student(name="A", fee=500_000)
    b = make_student(name="B", fee=300_000)
    pay(a["id"], 500_000, "2026-09-10")  # A paid in full
    pay(b["id"], 100_000, "2026-09-10")  # B did not
    body = debtors(client)
    assert [d["student_id"] for d in body["debtors"]] == [b["id"]]
    assert body["debtors"][0]["debt"] == 200_000


def test_sorted_by_debt_descending_and_totals(client, make_student, pay):
    small = make_student(name="small", fee=100_000)
    big = make_student(name="big", fee=900_000)
    mid = make_student(name="mid", fee=500_000)
    pay(mid["id"], 100_000, "2026-09-10")  # debt 400 000
    body = debtors(client)
    assert [d["student_id"] for d in body["debtors"]] == [big["id"], mid["id"], small["id"]]
    assert [d["debt"] for d in body["debtors"]] == [900_000, 400_000, 100_000]
    assert body["count"] == 3
    assert body["total_debt"] == 1_400_000


def test_no_students_means_no_debtors(client):
    body = debtors(client)
    assert body == {"month": SEPT, "count": 0, "total_debt": 0, "debtors": []}


def test_month_defaults_to_current(client, make_student):
    make_student(fee=1000)
    r = client.get("/debtors")
    assert r.status_code == 200
    assert r.json()["month"] == dt.date.today().strftime("%Y-%m")
    assert r.json()["count"] == 1


@pytest.mark.parametrize("month", ["2026-13", "2026-00", "2026-9", "26-09", "2026/09", "abc", "2026-09-01", ""])
def test_invalid_month_is_422(client, month):
    assert client.get("/debtors", params={"month": month}).status_code == 422
