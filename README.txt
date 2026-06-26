HouseZero one-year dataset build pipeline.

Source: figshare https://doi.org/10.6084/m9.figshare.30260233

Run:

    ./bootstrap.sh

Downloads per-table CSVs from figshare, merges them into one wide
data.csv with renamed canonical headers, and prints a summary.

Output: data.csv
Expected md5: 7e9c74507473c23d41ac72cb25195439

Files:
    build.py       merge + rename
    roundtrip.py   reconstruct per-table CSVs from data.csv and diff
    summary.py     print rows / columns / span / group counts
    rename.tsv     source_table  original  canonical
    rubric.tsv     canonical  unit  short_desc  long_desc

Requirements: python3, pandas, curl.
