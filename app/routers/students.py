import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_db
from app.schemas import StudentIn, StudentOut

router = APIRouter(prefix="/students", tags=["students"])

COLUMNS = 'id, name, phone, group_name AS "group", monthly_fee, created_at'


def get_student_or_404(conn: sqlite3.Connection, student_id: int) -> dict:
    row = conn.execute(f"SELECT {COLUMNS} FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return dict(row)


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(data: StudentIn, conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO students (name, phone, group_name, monthly_fee) VALUES (?, ?, ?, ?)",
        (data.name, data.phone, data.group, data.monthly_fee),
    )
    conn.commit()
    return get_student_or_404(conn, cur.lastrowid)


@router.get("", response_model=list[StudentOut])
def list_students(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(f"SELECT {COLUMNS} FROM students ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return get_student_or_404(conn, student_id)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, data: StudentIn, conn: sqlite3.Connection = Depends(get_db)):
    get_student_or_404(conn, student_id)
    conn.execute(
        "UPDATE students SET name = ?, phone = ?, group_name = ?, monthly_fee = ? WHERE id = ?",
        (data.name, data.phone, data.group, data.monthly_fee, student_id),
    )
    conn.commit()
    return get_student_or_404(conn, student_id)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, conn: sqlite3.Connection = Depends(get_db)):
    get_student_or_404(conn, student_id)
    # The student's payments go with them (ON DELETE CASCADE).
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
