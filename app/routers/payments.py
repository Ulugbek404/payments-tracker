import datetime as dt
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_db
from app.routers.students import get_student_or_404
from app.schemas import PaymentIn, PaymentOut

router = APIRouter(tags=["payments"])

COLUMNS = "id, student_id, amount, paid_at AS date, created_at"


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(data: PaymentIn, conn: sqlite3.Connection = Depends(get_db)):
    get_student_or_404(conn, data.student_id)
    paid_at = (data.date or dt.date.today()).isoformat()
    try:
        cur = conn.execute(
            "INSERT INTO payments (student_id, amount, paid_at) VALUES (?, ?, ?)",
            (data.student_id, data.amount, paid_at),
        )
    except sqlite3.IntegrityError:
        # The student was deleted between the check above and the insert.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    conn.commit()
    row = conn.execute(f"SELECT {COLUMNS} FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.get("/students/{student_id}/payments", response_model=list[PaymentOut])
def list_student_payments(student_id: int, conn: sqlite3.Connection = Depends(get_db)):
    get_student_or_404(conn, student_id)
    rows = conn.execute(
        f"SELECT {COLUMNS} FROM payments WHERE student_id = ? ORDER BY paid_at DESC, id DESC",
        (student_id,),
    ).fetchall()
    return [dict(r) for r in rows]
