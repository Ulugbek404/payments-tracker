import datetime as dt
import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_db
from app.queries import find_debtors
from app.schemas import MONTH_PATTERN, DebtorsOut

router = APIRouter(tags=["debtors"])


@router.get("/debtors", response_model=DebtorsOut)
def get_debtors(
    month: str | None = Query(
        default=None,
        pattern=MONTH_PATTERN,
        description="Month as YYYY-MM. Defaults to the current month.",
        examples=["2026-10"],
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    month = month or dt.date.today().strftime("%Y-%m")
    year, mon = int(month[:4]), int(month[5:])
    start = dt.date(year, mon, 1)
    end = dt.date(year + mon // 12, mon % 12 + 1, 1)  # first day of the next month

    debtors = find_debtors(conn, start.isoformat(), end.isoformat())
    return DebtorsOut(
        month=month,
        count=len(debtors),
        total_debt=sum(d["debt"] for d in debtors),
        debtors=debtors,
    )
