import os
import sys
import filecmp
import math
import pandas as pd

os.makedirs("roundtrip/out", exist_ok=True)
os.makedirs("roundtrip/ref", exist_ok=True)

rename = {}
with open("rename.tsv") as f:
    next(f)
    for line in f:
        ctx, orig, canon = line.rstrip("\n").split("\t")[:3]
        rename.setdefault(ctx, {})[canon] = orig

df = pd.read_csv("data.csv", dtype=str, keep_default_na=False)
df["Timestamp"] = (pd.to_datetime(df["timestamp"], utc=True)
                   .dt.tz_convert("America/New_York")
                   .dt.strftime("%Y-%m-%d %H:%M:%S%z")
                   .str.replace(r"(\d\d)(\d\d)$", r"\1:\2", regex=True))

def gfmt(s):
    def one(v):
        if v == "": return ""
        x = float(v)
        if not math.isfinite(x): return ""
        return f"{x:.6g}"
    return s.map(one)

bad = 0
for tbl, m in rename.items():
    canon, orig = list(m.keys()), list(m.values())
    out = df[["Timestamp"] + canon].rename(columns=dict(zip(canon, orig)))
    for c in orig: out[c] = gfmt(out[c])
    out.to_csv(f"roundtrip/out/{tbl}.csv", index=False, lineterminator="\n")

    ref = pd.read_csv(f"figshare/{tbl}.csv", dtype=str, keep_default_na=False)
    for c in orig: ref[c] = gfmt(ref[c])
    ref = ref[["Timestamp"] + orig]
    ref.to_csv(f"roundtrip/ref/{tbl}.csv", index=False, lineterminator="\n")

    same = filecmp.cmp(f"roundtrip/out/{tbl}.csv", f"roundtrip/ref/{tbl}.csv", shallow=False)
    print(f"  {'OK ' if same else '** '}  {tbl}")
    if not same: bad += 1

print(f"\nresult: {bad} table(s) differ")
sys.exit(1 if bad else 0)
