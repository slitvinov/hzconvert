import sys
import filecmp
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC  = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "figshare"
DC   = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "data.csv"
OUT  = HERE / "roundtrip" / "out"
REF  = HERE / "roundtrip" / "ref"
OUT.mkdir(parents=True, exist_ok=True)
REF.mkdir(parents=True, exist_ok=True)

rename = {}
with (HERE / "rename.tsv").open() as f:
    next(f)
    for line in f:
        ctx, orig, canon = line.rstrip("\n").split("\t")[:3]
        rename.setdefault(ctx, {})[canon] = orig

df = pd.read_csv(DC, dtype=str, keep_default_na=False)
df["Timestamp"] = (pd.to_datetime(df["timestamp"], utc=True)
                   .dt.tz_convert("America/New_York")
                   .dt.strftime("%Y-%m-%d %H:%M:%S%z")
                   .str.replace(r"(\d\d)(\d\d)$", r"\1:\2", regex=True))

def gfmt(s):
    return s.map(lambda v: "" if v == "" else f"{float(v):.6g}")

bad = 0
for tbl, m in rename.items():
    canon, orig = list(m.keys()), list(m.values())
    out = df[["Timestamp"] + canon].rename(columns=dict(zip(canon, orig)))
    for c in orig: out[c] = gfmt(out[c])
    out.to_csv(OUT / f"{tbl}.csv", index=False, lineterminator="\n")

    ref = pd.read_csv(SRC / f"{tbl}.csv", dtype=str, keep_default_na=False)
    for c in orig: ref[c] = gfmt(ref[c])
    ref = ref[["Timestamp"] + orig]
    ref.to_csv(REF / f"{tbl}.csv", index=False, lineterminator="\n")

    same = filecmp.cmp(OUT / f"{tbl}.csv", REF / f"{tbl}.csv", shallow=False)
    print(f"  {'OK ' if same else '** '}  {tbl}")
    if not same: bad += 1

print(f"\nresult: {bad} table(s) differ")
sys.exit(1 if bad else 0)
