# GST Automation (FastAPI + SQLite + plain HTML/JS)

## Run in VS Code
1. File > Open Folder > `gst-automation`
2. Terminal (Ctrl+`):
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows   (Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   cd backend
   uvicorn main:app --reload
   ```
3. Open http://127.0.0.1:8000  (API docs: http://127.0.0.1:8000/docs)
   Or select the venv as Python interpreter and press F5 (Run GST App).

## Features
- Create invoices; CGST+SGST (same state) or IGST (other state) auto-calculated
- GSTIN format validation; allowed rates 0/0.25/3/5/12/18/28
- Bulk upload from CSV (see data/sample_invoices.csv)
- Monthly tax summary
- GSTR-1 style CSV export (review before filing on the GST portal)

## Layout
backend/   main.py (API), gst.py (tax logic), database.py (SQLite)
frontend/  index.html, app.js, style.css
data/      sample CSV + gst.db (auto-created)

Set your company's state in `backend/gst.py` AND `frontend/app.js` (SELLER_STATE).
