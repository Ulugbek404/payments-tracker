import sqlite3

# Payments are summed per student first (the date filter lives inside this subquery),
# then joined to ALL students. A student without payments in the period gets paid = 0
# instead of disappearing, which is what a date filter in the outer WHERE would cause.
DEBTORS_SQL = """
SELECT student_id, name, phone, "group", monthly_fee, paid, debt
FROM (
    SELECT s.id                                   AS student_id,
           s.name                                 AS name,
           s.phone                                AS phone,
           s.group_name                           AS "group",
           s.monthly_fee                          AS monthly_fee,
           COALESCE(p.paid, 0)                    AS paid,
           s.monthly_fee - COALESCE(p.paid, 0)    AS debt
    FROM students AS s
    LEFT JOIN (
        SELECT student_id, SUM(amount) AS paid
        FROM payments
        WHERE paid_at >= :start AND paid_at < :end
        GROUP BY student_id
    ) AS p ON p.student_id = s.id
)
WHERE debt > 0
ORDER BY debt DESC, student_id
"""


def find_debtors(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """Students who paid less than their monthly_fee within the period [start, end).

    start, end -- ISO dates 'YYYY-MM-DD'. A payment counts if start <= paid_at < end.

    Returns one dict per debtor, sorted by debt descending (ties: by student id) with keys:
        student_id, name, phone, group, monthly_fee, paid, debt
    where paid = sum of the student's payments in the period (0 if there are none)
    and   debt = monthly_fee - paid (always > 0 -- fully paid and overpaid students are not listed).
    """
    rows = conn.execute(DEBTORS_SQL, {"start": start, "end": end}).fetchall()
    return [dict(r) for r in rows]
