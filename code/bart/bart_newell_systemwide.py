"""Systemwide Newell square-root benchmark on the observed BART weekday profile (8.7%).

Section 7.2 / Table 10 note b of the paper: a fixed daily number of departures
n is spread over the H = 19 operating hours (05..23).  With hourly arrival rate
lambda_h and f_h departures in hour h, continuum headway waiting is
    W(f) = sum_h lambda_h / (2 f_h)        (pax-h, one-hour bins)
  uniform:      f_h = n / H                -> W_u = H * sum(lambda) / (2 n)
  square root:  f_h = n sqrt(lambda_h) / sum sqrt(lambda)
                                           -> W_s = (sum sqrt(lambda))^2 / (2 n)
  saving = 1 - W_s / W_u = 1 - (sum sqrt(lambda))^2 / (H * sum lambda),
which does not depend on n.  lambda_h is the mean weekday profile over the 123
weekdays, same-station records excluded (see bart_observed_demand.py).

Ported from the "newell_normalized_shape_value" in the author's original
  .../adaptive-transit-voa-student-v1.9/release_packages/version_8/paper/tools/
  build_multiclock_demand_figure.py (lines 82-88).

Run from the repository root:
    python -I code/bart/bart_newell_systemwide.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OD_TD = ROOT / "data" / "BART" / "GMNS" / "OD_demand_td.csv"
OUT = Path(__file__).resolve().parent / "output"


def newell_saving(lam: np.ndarray) -> float:
    lam = np.asarray(lam, dtype=float)
    return 1.0 - np.sqrt(lam).sum() ** 2 / (len(lam) * lam.sum())


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cache = OUT / "weekday_day_hour_demand.csv"
    if cache.exists():
        mat = pd.read_csv(cache, index_col=0)
    else:
        df = pd.read_csv(OD_TD, usecols=["date", "hour", "day_type", "origin", "destination", "volume"])
        wk = df[(df.day_type == "Weekday") & (df.origin != df.destination)]
        mat = wk.groupby(["date", "hour"]).volume.sum().unstack(fill_value=0).sort_index()
    lam = mat.mean(axis=0).to_numpy(dtype=float)
    s = newell_saving(lam)
    n = 100  # any fixed departure total; the ratio does not depend on it
    W_u = len(lam) * lam.sum() / (2 * n)
    W_s = np.sqrt(lam).sum() ** 2 / (2 * n)
    res = {"n_weekdays": int(len(mat)), "hours": len(lam), "saving": s,
           "W_uniform_over_n100": W_u, "W_sqrt_over_n100": W_s,
           "sensitivity_hours_06_23": newell_saving(lam[1:]),
           "sensitivity_hours_05_22": newell_saving(lam[:-1])}
    (OUT / "newell_systemwide.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"{len(mat)} weekdays, {len(lam)} hours: square-root vs uniform saving = {100*s:.2f}%  (paper 8.7%)")
    print(f"  sensitivity: hours 06-23 {100*res['sensitivity_hours_06_23']:.2f}%, "
          f"hours 05-22 {100*res['sensitivity_hours_05_22']:.2f}%")


if __name__ == "__main__":
    main()
