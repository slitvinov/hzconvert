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
    fit.py         fit the nlLED twin from data.csv (GPU, ~30 min);
                   an optional zone argument (e.g. python fit.py Z31)
                   fits a single-zone model on that zone's air/slab
                   temperatures driven only by weather (incl. facade
                   temperature and wind) and its own valve and
                   windows, saved as fit.<zone>.pt
    fit.pt         trained joint-model checkpoint: cell/head weights,
                   normalization constants (ym ys um us zm zsd),
                   state/external names
    fit.<zone>.pt  single-zone checkpoints (fit.Z31.pt, fit.Z33.pt),
                   same layout as fit.pt but with that zone's two
                   states and its own externals
    rename.tsv     source_table  original  canonical
    rubric.tsv     canonical  unit  short_desc  long_desc

Single-zone models (free-running rollout RMSE, air temperature, F;
externals: weather, facade temperature, wind, own valve and windows):

    zone   year roll   val month   jan-roll
    Z31    1.22        1.38        1.18
    Z33    0.87        1.41        0.87

Requirements: python3, pandas, curl.
fit.py additionally needs numpy, torch, holidays; it trains an LSTM
on the 37 zone air/slab temperatures driven by weather, the 19 valve
commands, and calendar inputs, saves fit.pt, and prints free-running
rollout checks (full year, held-out May 2025, January onward).
