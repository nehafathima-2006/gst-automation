const SELLER_STATE = "Karnataka"; // keep in sync with backend/gst.py
const STATES = ["Andhra Pradesh","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat","Haryana","Himachal Pradesh",
"Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Odisha","Punjab","Rajasthan","Tamil Nadu",
"Telangana","Uttar Pradesh","Uttarakhand","West Bengal"];
const RATES = [0, 5, 12, 18, 28];
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money = n => "₹" + Number(n || 0).toLocaleString("en-IN", {minimumFractionDigits: 2, maximumFractionDigits: 2});

$("#seller").textContent = "Seller state: " + SELLER_STATE;
$("#pos").innerHTML = STATES.map(s => `<option ${s === SELLER_STATE ? "selected" : ""}>${s}</option>`).join("");
$("#date").valueAsDate = new Date();

function addRow() {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td><input class="d"></td><td><input class="h" size="6"></td>
    <td><input class="q" type="number" min="0" step="any" value="1"></td>
    <td><input class="r" type="number" min="0" step="any" value="0"></td>
    <td><select class="g">${RATES.map(r => `<option ${r === 18 ? "selected" : ""}>${r}</option>`).join("")}</select></td>
    <td class="t">0.00</td><td><button class="sec x">✕</button></td>`;
  tr.addEventListener("input", preview);
  tr.querySelector(".x").onclick = () => { tr.remove(); preview(); };
  $("#items tbody").appendChild(tr);
}

function getItems() {
  return [...document.querySelectorAll("#items tbody tr")].map(tr => ({
    description: tr.querySelector(".d").value.trim(),
    hsn: tr.querySelector(".h").value.trim(),
    qty: parseFloat(tr.querySelector(".q").value) || 0,
    rate: parseFloat(tr.querySelector(".r").value) || 0,
    gst_rate: parseFloat(tr.querySelector(".g").value),
    row: tr
  }));
}

function preview() {
  const intra = $("#pos").value === SELLER_STATE;
  let taxable = 0, tax = 0;
  getItems().forEach(i => {
    const t = i.qty * i.rate;
    i.row.querySelector(".t").textContent = t.toFixed(2);
    taxable += t; tax += t * i.gst_rate / 100;
  });
  $("#preview").innerHTML = `Taxable: <b>${money(taxable)}</b> &nbsp;
    ${intra ? `CGST: ${money(tax / 2)} &nbsp; SGST: ${money(tax / 2)}` : `IGST: ${money(tax)}`}
    &nbsp; Total: <b>${money(taxable + tax)}</b>`;
}

async function api(url, opts) {
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || "Error"));
  return data;
}

async function save() {
  const msg = $("#msg");
  try {
    const body = {
      invoice_no: $("#invoice_no").value.trim(), date: $("#date").value,
      customer_name: $("#customer_name").value.trim(), customer_gstin: $("#customer_gstin").value.trim(),
      place_of_supply: $("#pos").value,
      items: getItems().map(({row, ...i}) => i)
    };
    await api("/api/invoices", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    msg.className = "ok"; msg.textContent = "Saved ✔";
    $("#invoice_no").value = ""; $("#items tbody").innerHTML = ""; addRow(); preview(); load();
  } catch (e) { msg.className = "err"; msg.textContent = e.message; }
}

async function load() {
  const [inv, sum] = await Promise.all([api("/api/invoices"), api("/api/summary")]);
  $("#summary").innerHTML = "<tr><th>Month</th><th>Invoices</th><th>Taxable</th><th>CGST</th><th>SGST</th><th>IGST</th><th>Total</th></tr>" +
    sum.map(s => `<tr><td>${esc(s.month)}</td><td>${s.invoices}</td><td>${money(s.taxable)}</td><td>${money(s.cgst)}</td><td>${money(s.sgst)}</td><td>${money(s.igst)}</td><td>${money(s.total)}</td></tr>`).join("");
  $("#invoices").innerHTML = "<tr><th>No</th><th>Date</th><th>Customer</th><th>GSTIN</th><th>Taxable</th><th>Tax</th><th>Total</th><th></th></tr>" +
    inv.map(i => `<tr><td>${esc(i.invoice_no)}</td><td>${esc(i.date)}</td><td>${esc(i.customer_name)}</td><td>${esc(i.customer_gstin)}</td><td>${money(i.taxable)}</td><td>${money(i.cgst + i.sgst + i.igst)}</td><td>${money(i.total)}</td><td><button class="sec" onclick="del(${i.id})">Delete</button></td></tr>`).join("");
}

async function del(id) {
  if (confirm("Delete this invoice?")) { await api("/api/invoices/" + id, {method: "DELETE"}); load(); }
}

async function upload() {
  const f = $("#csv").files[0];
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  try {
    const r = await api("/api/upload", {method: "POST", body: fd});
    $("#uploadMsg").innerHTML = `<p class="ok">Imported ${r.imported} invoice(s)</p>` +
      r.errors.map(e => `<p class="err">${esc(e)}</p>`).join("");
    load();
  } catch (e) { $("#uploadMsg").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
}

$("#addRow").onclick = addRow;
$("#save").onclick = save;
$("#upload").onclick = upload;
$("#pos").onchange = preview;
addRow(); preview(); load();
