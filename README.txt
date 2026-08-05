HouseZero one-year dataset build pipeline.

Source: figshare https://doi.org/10.6084/m9.figshare.30260233

Run:

    ./bootstrap.sh

Downloads per-table CSVs from figshare, merges them into one wide
data.csv with renamed canonical headers, and prints a summary.

Output: data.csv
Expected md5: a819477def45d4d00e1ab3fdb6dc51bb

Files:
    build.py       merge + rename
    roundtrip.py   reconstruct per-table CSVs from data.csv and diff
    summary.py     print rows / columns / span / group counts
    fit.py         fit the nlLED twin from data.csv (GPU, ~30 min)
    fit.pt         trained checkpoint: cell/head weights, normalization
                   constants (ym ys um us zm zsd), state/external names
    rename.tsv     source_table  original  canonical
    rubric.tsv     canonical  unit  short_desc  long_desc

Requirements: python3, pandas, curl.
fit.py additionally needs numpy, torch, holidays; it trains an LSTM
on the 37 zone air/slab temperatures driven by weather, the 19 valve
commands, and calendar inputs, saves fit.pt, and prints free-running
rollout checks (full year, held-out May 2025, January onward).
