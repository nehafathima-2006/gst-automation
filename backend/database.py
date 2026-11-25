import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "gst.db"


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init():
    DB.parent.mkdir(exist_ok=True)
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_gstin TEXT,
            place_of_supply TEXT NOT NULL,
            taxable REAL, cgst REAL, sgst REAL, igst REAL, total REAL);
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            description TEXT, hsn TEXT, qty REAL, rate REAL, gst_rate REAL,
            taxable REAL, cgst REAL, sgst REAL, igst REAL);
        """)
