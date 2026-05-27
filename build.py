import csv
import math

rename = {}
with open("rename.tsv") as f:
    next(f)
    for line in f:
        ctx, orig, canon = line.rstrip("\n").split("\t")[:3]
        rename.setdefault(ctx, {})[orig] = canon

order = []
with open("rubric.tsv") as f:
    next(f)
    for line in f:
        order.append(line.split("\t", 1)[0])

streams = {}
canon_src = {}
for tbl, m in rename.items():
    fp = open(f"figshare/{tbl}.csv")
    rdr = csv.reader(fp)
    header = next(rdr)
    streams[tbl] = (fp, rdr)
    for i, h in enumerate(header):
        if h in m:
            canon_src[m[h]] = (tbl, i)

dispatch = [canon_src[c] for c in order]

def fmt(v):
    if v == "": return ""
    try:
        x = float(v)
    except ValueError:
        return v
    if not math.isfinite(x):
        return ""
    return f"{x:.6g}"

n = 0
with open("data.csv", "w", newline="") as out:
    out.write("timestamp," + ",".join(order) + "\n")
    while True:
        rows = {}
        try:
            for tbl, (_, rdr) in streams.items():
                rows[tbl] = next(rdr)
        except StopIteration:
            break
        ts = next(iter(rows.values()))[0]
        ts = f"{ts[:10]}T{ts[11:19]}{ts[19:22]}{ts[23:]}"
        out.write(ts)
        for tbl, idx in dispatch:
            out.write(",")
            out.write(fmt(rows[tbl][idx]))
        out.write("\n")
        n += 1

for fp, _ in streams.values():
    fp.close()
print(f"wrote data.csv  ({n:,} rows x {len(order)} cols)")
