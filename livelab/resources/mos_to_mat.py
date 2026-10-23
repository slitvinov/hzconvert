#!/usr/bin/env python3
import argparse
import re
import sys

import numpy as np
import scipy.io

ALIASES = {
    "Tdry":   "Dry bulb temperature",
    "Tdew":   "Dew point temperature",
    "RH":     "Relative humidity",
    "GHR":    "Global horizontal radiation",
    "DNR":    "Direct normal radiation",
    "DHR":    "Diffuse horizontal radiation",
    "winDir": "Wind direction",
    "winSpe": "Wind speed",
    "pres":   "Atmospheric station pressure",
}
DEFAULT_COLS = "Tdry,RH,GHR,winDir,winSpe"

def parse_headers(path):
    headers = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"#C(\d+)\s*(.*)", line)
            if m:
                headers[int(m.group(1)) - 1] = m.group(2).strip()
    return headers

def resolve_cols(headers, requested):
    indices = []
    for name in requested:
        descr_substr = ALIASES.get(name, name).lower()
        match = next(
            (idx for idx, descr in headers.items() if descr_substr in descr.lower()),
            None,
        )
        if match is None:
            raise SystemExit(
                f"mos_to_mat: cannot find column '{name}' "
                f"(looking for substring '{descr_substr}'). "
                f"Available headers: {list(headers.values())}"
            )
        indices.append(match)
    return indices

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--cols", default=DEFAULT_COLS)
    args = ap.parse_args()

    headers = parse_headers(args.infile)
    if not headers:
        sys.exit(f"mos_to_mat: no #C<n> column headers found in {args.infile}")

    requested = [c.strip() for c in args.cols.split(",") if c.strip()]
    data_idx = resolve_cols(headers, requested)
    print("# resolved columns: " +
          ", ".join(f"{name}=C{idx+1}" for name, idx in zip(requested, data_idx)),
          file=sys.stderr)

    rows = []
    with open(args.infile) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("double "):
                continue
            parts = line.split()
            try:
                rows.append([float(parts[c]) for c in [0] + data_idx])
            except (IndexError, ValueError):
                continue

    arr = np.asarray(rows, dtype=np.float64)
    t = arr[:, 0]
    out = {name: np.column_stack((t, arr[:, 1 + i]))
           for i, name in enumerate(requested)}
    scipy.io.savemat(args.outfile, out, format="4")
    print(f"# wrote {arr.shape[0]} rows for {len(requested)} signals to {args.outfile}: " +
          ", ".join(requested), file=sys.stderr)

if __name__ == "__main__":
    main()
