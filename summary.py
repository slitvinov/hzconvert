import sys
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
DC   = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data.csv"

df = pd.read_csv(DC, nrows=0)
cols = [c for c in df.columns if c != "timestamp"]
prefixes = {}
for c in cols:
    p = c.split("/", 1)[0]
    prefixes[p] = prefixes.get(p, 0) + 1

with DC.open() as f:
    next(f)
    first = next(f).split(",", 1)[0]
    for line in f:
        pass
    last = line.split(",", 1)[0]

n_rows = sum(1 for _ in DC.open()) - 1

print(f"file:    {DC}")
print(f"rows:    {n_rows:,}")
print(f"columns: {len(cols)}")
print(f"span:    {first}  ..  {last}")
print(f"groups:")
for p, n in sorted(prefixes.items()):
    print(f"  {p:12s}  {n:3d}")
