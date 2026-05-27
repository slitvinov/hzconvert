import sys
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC  = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "figshare"
OUT  = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "data.csv"

rename = {}
with (HERE / "rename.tsv").open() as f:
    next(f)
    for line in f:
        ctx, orig, canon = line.rstrip("\n").split("\t")[:3]
        rename.setdefault(ctx, {})[orig] = canon

order = pd.read_csv(HERE / "rubric.tsv", sep="\t")["name"].tolist()

frames = []
for tbl, m in rename.items():
    df = pd.read_csv(SRC / f"{tbl}.csv")
    df = df.rename(columns={"Timestamp": "timestamp", **m})
    df["timestamp"] = (pd.to_datetime(df["timestamp"], utc=True)
                       .dt.tz_convert("America/New_York")
                       .dt.strftime("%Y-%m-%dT%H:%M:%S%z"))
    frames.append(df.set_index("timestamp"))

merged = pd.concat(frames, axis=1)[order]
merged.to_csv(OUT, float_format="%.6g")
print(f"wrote {OUT}  ({len(merged):,} rows x {merged.shape[1]} cols)")
