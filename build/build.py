"""Build the firm dashboard from MyCase payment exports + the phone analytics export.

Usage: python3 build.py <folder with CSVs> <output.html> [manual.json]
manual.json holds figures typed in chat for days not yet exported:
  {"payments":[{"d":"2026-10-27","a":"Criminal","amt":1500}], "calls":{"2026-10-27":32}}
Exports always win: typed payments for a practice area are dropped for any date
an export of that area covers, and typed calls are dropped for any day the call
export covers.
Expects files whose names start with Crim, PI, EP, Civil (payment exports)
and analytics-table (call counts). Client names are NOT carried into the page,
so the output is safe to host publicly for a HubSpot embed.
"""
import sys, glob, os, json, datetime
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "."
out = sys.argv[2] if len(sys.argv) > 2 else "dashboard.html"
manual_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "manual.json")
here = os.path.dirname(os.path.abspath(__file__))

AREAS = [("Criminal", "Crim"), ("Personal Injury", "PI"),
         ("Estate Planning", "EP"), ("Civil Litigation", "Civil")]

def method(m, refund):
    m = str(m)
    if refund or m.startswith("Refund"): return "Refund"
    if m == "Trust": return "Trust transfer"
    if m == "Check": return "Check"
    if "eCheck" in m: return "eCheck"
    if m == "Other": return "Affirm / financing"
    if "payment plan" in m: return "Card, payment plan"
    return "Card"

def truthy(v):
    return str(v).strip().upper() == "TRUE"

payments = []
covered = {}  # area -> (first, last) date the exports cover
for area, prefix in AREAS:
    files = sorted(glob.glob(os.path.join(src, prefix + "*.csv")))
    for f in files:
        df = pd.read_csv(f)
        if df.empty: continue
        ds = pd.to_datetime(df["Date"])
        lo, hi = ds.max().replace(day=1).strftime("%Y-%m-%d"), ds.max().strftime("%Y-%m-%d")
        if area in covered: lo, hi = min(lo, covered[area][0]), max(hi, covered[area][1])
        covered[area] = (lo, hi)
        for _, r in df.iterrows():
            refund = truthy(r.get("Refund"))
            payments.append({
                "d": pd.to_datetime(r["Date"]).strftime("%Y-%m-%d"),
                "a": area,
                "amt": round(float(r["Amount"]), 2),
                "id": int(r["MyCase ID"]),
            })

# de-duplicate by MyCase ID so overlapping exports never double count
payments = list({p["id"]: p for p in payments}.values())
for p in payments: del p["id"]

calls = {}
cf = sorted(glob.glob(os.path.join(src, "analytics-table*.csv")))
if cf:
    c = pd.read_csv(cf[-1], encoding="utf-8-sig")
    c = c.set_index(c.columns[0])
    for col in c.columns:
        dt = datetime.datetime.strptime(col, "%m-%d-%Y").strftime("%Y-%m-%d")
        calls[dt] = {k: int(c.loc[k, col]) for k in c.index}

manual = {"payments": [], "calls": {}}
if os.path.exists(manual_path):
    manual = json.load(open(manual_path))
kept = 0
for p in manual.get("payments", []):
    cov = covered.get(p["a"])
    if cov and cov[0] <= p["d"] <= cov[1]: continue
    payments.append({"d": p["d"], "a": p["a"], "amt": round(float(p["amt"]), 2)}); kept += 1
for d, n in manual.get("calls", {}).items():
    if d not in calls: calls[d] = {"Inbound": int(n)}; kept += 1
print(f"{kept} typed entries used")

data = {
    "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "areas": [a for a, _ in AREAS],
    "payments": sorted(payments, key=lambda p: p["d"]),
    "calls": calls,
}

tpl = open(os.path.join(here, "template.html"), encoding="utf-8").read()
html = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
open(out, "w", encoding="utf-8").write(html)
print(f"{len(payments)} payments, {len(calls)} call days -> {out}")
