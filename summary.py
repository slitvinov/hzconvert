with open("data.csv") as f:
    header = next(f).rstrip("\n").split(",")
    first = next(f).split(",", 1)[0]
    n = 1
    for line in f:
        n += 1
        last = line.split(",", 1)[0]

cols = header[1:]
prefixes = {}
for c in cols:
    p = c.split("/", 1)[0]
    prefixes[p] = prefixes.get(p, 0) + 1

print(f"rows:    {n:,}")
print(f"columns: {len(cols)}")
print(f"span:    {first}  ..  {last}")
print(f"groups:")
for p, k in sorted(prefixes.items()):
    print(f"  {p:12s}  {k:3d}")
