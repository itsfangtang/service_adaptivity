"""Observed 24th St Mission (24TH) hourly boardings behind Figures 3 and 6.

Figure 3(a) (two clocks): observed arrivals at 24th St Mission, Mon-Thu 2-5 October 2023.
Figure 3(b): cumulative arrivals at 24th St Mission on Tue 8 October 2019.
Figure 6 (regimes): mean of Mon-Thu 7-10 October 2019 (peak 2,362 pax/h at 08:00).

Source: data/BART/demand.csv.gz (all 1,924 archived dates, 2019-10-01..2025-04-01).
The figure titles quote 2,362 pax/h, which is the mean INCLUDING same-station
records (excluding them gives 2,357.5); both variants are written out.
The archive holds hours 05..23 only, so the 00:00-04:00 segment drawn in
Figure 3(a) cannot be recovered from this repository.

Run from the repository root:
    python -I code/bart/bart_24th_profiles.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "BART" / "demand.csv.gz"
OUT = Path(__file__).resolve().parent / "output"
STATION = "24TH"
DATES_2019 = ["2019-10-07", "2019-10-08", "2019-10-09", "2019-10-10"]
DATES_2023 = ["2023-10-02", "2023-10-03", "2023-10-04", "2023-10-05"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    keep = set(DATES_2019 + DATES_2023)
    parts = []
    for chunk in pd.read_csv(RAW, usecols=["date", "hour", "origin", "destination", "volume"], chunksize=2_000_000):
        parts.append(chunk[(chunk.origin == STATION) & chunk.date.isin(keep)])
    df = pd.concat(parts)
    rows = []
    for label, sub in [("incl_same_station", df), ("excl_same_station", df[df.destination != STATION])]:
        t = sub.groupby(["date", "hour"]).volume.sum().unstack(fill_value=0)
        t.loc["mean_2019-10-07_10"] = t.loc[DATES_2019].mean()
        t.loc["mean_2023-10-02_05"] = t.loc[DATES_2023].mean()
        t.insert(0, "variant", label)
        rows.append(t)
    res = pd.concat(rows)
    res.to_csv(OUT / "fig03_fig06_24th_profiles.csv")
    inc = rows[0]
    print("Figure 6 rates (mean Mon-Thu 7-10 Oct 2019, incl. same-station), 06..12:")
    print("  " + ", ".join(f"{h}:00 {inc.loc['mean_2019-10-07_10', h]:.1f}" for h in range(6, 13)))
    print(f"Figure 3(b) cumulative 05:00-12:00 on 2019-10-08: {inc.loc['2019-10-08', list(range(5, 12))].sum():,.0f}")
    print("Figure 3(a) 08:00 boardings, 2-5 Oct 2023:",
          ", ".join(f"{d} {inc.loc[d, 8]:.0f}" for d in DATES_2023))


if __name__ == "__main__":
    main()
