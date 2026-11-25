"""Database layer.
- If the DATABASE_URL environment variable is set -> external PostgreSQL.
- Otherwise -> local SQLite file (data/gst.db), handy for quick local testing.
"""
import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_PG = bool(DATABASE_URL)
DB = Path(__file__).resolve().parent.parent / "data" / "gst.db"

if USE_PG:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityError = psycopg.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError


class Conn:
    """Small wrapper so the rest of the code works the same on both databases."""

    def __init__(self):
        if USE_PG:
            self.c = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            self.c = sqlite3.connect(DB)
            self.c.row_factory = sqlite3.Row
            self.c.execute("PRAGMA foreign_keys=ON")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.c.rollback() if exc_type else self.c.commit()
        self.c.close()

    def execute(self, sql, params=()):
        if USE_PG:
            sql = sql.replace("?", "%s")
        return self.c.execute(sql, params)


def conn():
    return Conn()


def insert_returning_id(c, sql, params):
    if USE_PG:
        return c.execute(sql + " RETURNING id", params).fetchone()["id"]
    return c.execute(sql, params).lastrowid


PK = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
NUM = "DOUBLE PRECISION" if USE_PG else "REAL"

SCHEMA = [
    f"""CREATE TABLE IF NOT EXISTS invoices(
        id {PK},
        invoice_no TEXT UNIQUE NOT NULL,
        date TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_gstin TEXT,
        place_of_supply TEXT NOT NULL,
        taxable {NUM}, cgst {NUM}, sgst {NUM}, igst {NUM}, total {NUM})""",
    f"""CREATE TABLE IF NOT EXISTS items(
        id {PK},
        invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
        description TEXT, hsn TEXT, qty {NUM}, rate {NUM}, gst_rate {NUM},
        taxable {NUM}, cgst {NUM}, sgst {NUM}, igst {NUM})""",
]


def init():
    if not USE_PG:
        DB.parent.mkdir(exist_ok=True)
    with conn() as c:
        for stmt in SCHEMA:
            c.execute(stmt)
