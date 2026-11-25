import csv, io, sqlite3
from collections import defaultdict
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database as db
import gst

FRONT = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="GST Automation")
db.init()


class Item(BaseModel):
    description: str
    hsn: str = ""
    qty: float = Field(gt=0)
    rate: float = Field(ge=0)
    gst_rate: float


class InvoiceIn(BaseModel):
    invoice_no: str
    date: str  # YYYY-MM-DD
    customer_name: str
    customer_gstin: str = ""
    place_of_supply: str
    items: List[Item] = Field(min_length=1)


def save_invoice(inv: InvoiceIn):
    gstin = inv.customer_gstin.strip().upper()
    if not gst.valid_gstin(gstin):
        raise HTTPException(400, f"Invalid GSTIN: {gstin}")
    try:
        rows, tot = gst.compute([i.model_dump() for i in inv.items], inv.place_of_supply)
    except ValueError as e:
        raise HTTPException(400, str(e))
    with db.conn() as c:
        try:
            cur = c.execute(
                "INSERT INTO invoices(invoice_no,date,customer_name,customer_gstin,place_of_supply,"
                "taxable,cgst,sgst,igst,total) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (inv.invoice_no, inv.date, inv.customer_name, gstin, inv.place_of_supply,
                 tot["taxable"], tot["cgst"], tot["sgst"], tot["igst"], tot["total"]))
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"Invoice {inv.invoice_no} already exists")
        for r in rows:
            c.execute(
                "INSERT INTO items(invoice_id,description,hsn,qty,rate,gst_rate,taxable,cgst,sgst,igst) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (cur.lastrowid, r["description"], r["hsn"], r["qty"], r["rate"], r["gst_rate"],
                 r["taxable"], r["cgst"], r["sgst"], r["igst"]))
    return {"id": cur.lastrowid, **tot}


@app.post("/api/invoices")
def create_invoice(inv: InvoiceIn):
    return save_invoice(inv)


@app.get("/api/invoices")
def list_invoices():
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM invoices ORDER BY date DESC, id DESC")]


@app.get("/api/invoices/{inv_id}")
def get_invoice(inv_id: int):
    with db.conn() as c:
        inv = c.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
        if not inv:
            raise HTTPException(404, "Not found")
        items = [dict(r) for r in c.execute("SELECT * FROM items WHERE invoice_id=?", (inv_id,))]
    return {**dict(inv), "items": items}


@app.delete("/api/invoices/{inv_id}")
def delete_invoice(inv_id: int):
    with db.conn() as c:
        c.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
    return {"deleted": inv_id}


@app.get("/api/summary")
def summary():
    with db.conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT substr(date,1,7) AS month, COUNT(*) AS invoices, ROUND(SUM(taxable),2) AS taxable,"
            "ROUND(SUM(cgst),2) AS cgst, ROUND(SUM(sgst),2) AS sgst, ROUND(SUM(igst),2) AS igst,"
            "ROUND(SUM(total),2) AS total FROM invoices GROUP BY month ORDER BY month DESC")]


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """CSV columns: invoice_no,date,customer_name,customer_gstin,place_of_supply,
    description,hsn,qty,rate,gst_rate  (one row per line item)"""
    text = (await file.read()).decode("utf-8-sig")
    groups = defaultdict(list)
    for row in csv.DictReader(io.StringIO(text)):
        groups[row["invoice_no"].strip()].append(row)
    ok, errors = 0, []
    for no, rows in groups.items():
        h = rows[0]
        try:
            inv = InvoiceIn(
                invoice_no=no, date=h["date"].strip(), customer_name=h["customer_name"].strip(),
                customer_gstin=h.get("customer_gstin", ""), place_of_supply=h["place_of_supply"].strip(),
                items=[Item(description=r["description"], hsn=r.get("hsn", ""), qty=float(r["qty"]),
                            rate=float(r["rate"]), gst_rate=float(r["gst_rate"])) for r in rows])
            save_invoice(inv)
            ok += 1
        except HTTPException as e:
            errors.append(f"{no}: {e.detail}")
        except Exception as e:
            errors.append(f"{no}: {e}")
    return {"imported": ok, "errors": errors}


@app.get("/api/export/gstr1")
def export_gstr1():
    """Rate-wise sheet, ready to review before filing."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Recipient GSTIN", "Customer", "Invoice No", "Invoice Date", "Invoice Value",
                "Place of Supply", "HSN", "GST Rate %", "Taxable Value", "CGST", "SGST", "IGST"])
    with db.conn() as c:
        for r in c.execute("SELECT i.*, t.hsn, t.gst_rate, t.taxable AS t_tax, t.cgst AS t_cgst,"
                           "t.sgst AS t_sgst, t.igst AS t_igst FROM invoices i JOIN items t "
                           "ON t.invoice_id=i.id ORDER BY i.date, i.invoice_no"):
            w.writerow([r["customer_gstin"], r["customer_name"], r["invoice_no"], r["date"], r["total"],
                        r["place_of_supply"], r["hsn"], r["gst_rate"], r["t_tax"], r["t_cgst"],
                        r["t_sgst"], r["t_igst"]])
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=gstr1_export.csv"})


# Frontend is served by the same server -> one command runs everything
app.mount("/", StaticFiles(directory=FRONT, html=True), name="frontend")
