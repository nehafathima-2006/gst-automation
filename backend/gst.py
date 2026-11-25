import re

SELLER_STATE = "Karnataka"   # <-- change to your company's state
VALID_RATES = {0, 0.25, 3, 5, 12, 18, 28}
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def valid_gstin(g: str) -> bool:
    return not g or bool(GSTIN_RE.match(g))


def compute(items, place_of_supply):
    """Same state -> CGST+SGST (half each). Different state -> IGST."""
    intra = place_of_supply.strip().lower() == SELLER_STATE.lower()
    out, tot = [], dict(taxable=0.0, cgst=0.0, sgst=0.0, igst=0.0)
    for it in items:
        if it["gst_rate"] not in VALID_RATES:
            raise ValueError(f"Invalid GST rate {it['gst_rate']}. Allowed: {sorted(VALID_RATES)}")
        taxable = round(it["qty"] * it["rate"], 2)
        tax = round(taxable * it["gst_rate"] / 100, 2)
        if intra:
            cgst = round(tax / 2, 2); sgst = round(tax - cgst, 2); igst = 0.0
        else:
            cgst = sgst = 0.0; igst = tax
        out.append({**it, "taxable": taxable, "cgst": cgst, "sgst": sgst, "igst": igst})
        for k, v in (("taxable", taxable), ("cgst", cgst), ("sgst", sgst), ("igst", igst)):
            tot[k] = round(tot[k] + v, 2)
    tot["total"] = round(tot["taxable"] + tot["cgst"] + tot["sgst"] + tot["igst"], 2)
    return out, tot
