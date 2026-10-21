import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

# "group" is a reserved word in SQL, so the column is called group_name.
# Dates are stored as ISO strings (YYYY-MM-DD): they sort and compare correctly as text.
SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    phone       TEXT    NOT NULL,
    group_name  TEXT    NOT NULL,
    monthly_fee INTEGER NOT NULL CHECK (monthly_fee > 0),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    amount     INTEGER NOT NULL CHECK (amount > 0),
    paid_at    TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- (student_id, paid_at): one student's payments; (paid_at): the month range scan behind /debtors.
CREATE INDEX IF NOT EXISTS idx_payments_student_date ON payments (student_id, paid_at);
CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments (paid_at);
"""


def db_path() -> Path:
    # Read on every call so tests can point DB_PATH at a temporary file.
    return Path(os.environ.get("DB_PATH", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs sync endpoints and dependencies in a
    # thread pool, so one request may touch the connection from different threads.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Off by default in SQLite; without it ON DELETE CASCADE silently does nothing.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
