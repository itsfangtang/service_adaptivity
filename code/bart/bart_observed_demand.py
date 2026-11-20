"""Observed BART weekday demand: Section 7.2 statistics and Figure 11 data.

Reproduces, from the archived hourly OD records in this repository:
  * 174 dates (2024-10-01 .. 2025-04-01) and 123 weekdays,
  * mean weekday boardings 167,988 and coefficient of variation 0.149,
  * the mean hour-of-day profile (2,176 pax/h at 05:00, 18,246 at 08:00,
    19,728 at 17:00), the 10th-90th percentile band and the daily totals,
  * the square-root and uniform dispatch shares of Figure 11(c).

Conventions (ported from the author's original script
  Adaptive_Transit_VoA_Local_Project_2026-08-02/student_repo_packages/
  adaptive-transit-voa-student-v1.9/release_packages/version_8/paper/tools/
  build_multiclock_demand_figure.py, function load_day_hour_matrix):
  * weekday  = day_type == "Weekday" (identical to Monday-Friday here);
  * holidays = not filtered by rule: holiday dates are simply absent from the
    archive (11 Nov, 28-29 Nov, 25 Dec 2024, 1 Jan, 20 Jan, 17 Feb 2025;
    also missing: Sat 15 Feb and Mon 31 Mar 2025), so every weekday present
    is a "non-holiday weekday";
  * same-station records (origin == destination) are excluded;
  * hours 05..23 (the only hours in the archive), one-hour bins.

Run from the repository root:
    python -I code/bart/bart_observed_demand.py
Outputs go to code/bart/output/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OD_TD = ROOT / "data" / "BART" / "GMNS" / "OD_demand_td.csv"
OUT = Path(__file__).resolve().parent / "output"


def load_weekday_matrix() -> tuple[pd.DataFrame, pd.Series]:
    """Return (123 x 19 weekday date-hour boardings matrix, day_type by date)."""
    df = pd.read_csv(OD_TD, usecols=["date", "hour", "day_type", "origin", "destination", "volume"])
    day_type = df.groupby("date").day_type.first()
    wk = df[(df.day_type == "Weekday") & (df.origin != df.destination)]
    mat = wk.groupby(["date", "hour"]).volume.sum().unstack(fill_value=0).sort_index()
    return mat, day_type


def main() -> None:
    OUT.mkdir(exist_ok=True)
    mat, day_type = load_weekday_matrix()
    dates = pd.to_datetime(day_type.index)
    hours = np.array([int(h) for h in mat.columns])

    mean = mat.mean(axis=0)
    p10 = mat.quantile(0.10, axis=0)
    p90 = mat.quantile(0.90, axis=0)
    daily = mat.sum(axis=1)

    q = mean.to_numpy(dtype=float)
    sqrt_share = np.sqrt(q) / np.sqrt(q).sum()
    demand_share = q / q.sum()
    uniform_share = np.full_like(q, 1.0 / len(q))

    stats = {
        "n_dates": int(len(day_type)),
        "date_min": str(dates.min().date()),
        "date_max": str(dates.max().date()),
        "day_type_counts": {k: int(v) for k, v in day_type.value_counts().items()},
        "n_weekdays_used": int(len(mat)),
        "weekday_equals_mon_fri": bool(((dates.dayofweek < 5) == (day_type.values == "Weekday")).all()),
        "missing_calendar_dates": [
            d.strftime("%a %Y-%m-%d")
            for d in pd.date_range(dates.min(), dates.max()).difference(dates)
        ],
        "daily_total_mean": float(daily.mean()),
        "daily_total_cv_ddof1": float(daily.std(ddof=1) / daily.mean()),
        "daily_total_cv_ddof0": float(daily.std(ddof=0) / daily.mean()),
        "daily_total_min": [str(daily.idxmin()), float(daily.min())],
        "daily_total_max": [str(daily.idxmax()), float(daily.max())],
        "mean_profile_pax_per_h": {int(h): round(float(v), 1) for h, v in zip(hours, q)},
    }
    (OUT / "observed_demand_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    mat.to_csv(OUT / "weekday_day_hour_demand.csv")
    pd.DataFrame({
        "hour": hours, "mean": q, "p10": p10.to_numpy(), "p90": p90.to_numpy(),
        "demand_share": demand_share, "sqrt_share": sqrt_share, "uniform_share": uniform_share,
    }).to_csv(OUT / "fig11_profile.csv", index=False)
    pd.DataFrame({"date": daily.index, "total": daily.values,
                  "rolling5": daily.rolling(5, center=True, min_periods=1).mean().values}
                 ).to_csv(OUT / "fig11_daily_totals.csv", index=False)

    print(f"dates: {stats['n_dates']} ({stats['date_min']} .. {stats['date_max']}), "
          f"day types {stats['day_type_counts']}")
    print("missing calendar dates:", ", ".join(stats["missing_calendar_dates"]))
    print(f"weekdays used: {stats['n_weekdays_used']}")
    print(f"mean weekday boardings: {stats['daily_total_mean']:,.1f}  (paper 167,988)")
    print(f"CV: {stats['daily_total_cv_ddof1']:.4f} (ddof=1), {stats['daily_total_cv_ddof0']:.4f} (ddof=0)  (paper 0.149)")
    print(f"05:00 {q[0]:,.0f}  08:00 {mean[8]:,.0f}  17:00 {mean[17]:,.0f}  (paper 2,176 / 18,246 / 19,728)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)
    ax[0].fill_between(hours, p10 / 1e3, p90 / 1e3, color="#d9534f", alpha=0.25, lw=0, label="10th-90th percentile")
    ax[0].plot(hours, q / 1e3, "o-", color="#c0392b", label="mean")
    ax[0].set(xlabel="Hour of day", ylabel="Boardings (thousand/h)", xticks=[5, 8, 12, 16, 20, 23])
    ax[0].legend(frameon=False)
    dd = pd.to_datetime(daily.index)
    ax[1].plot(dd, daily / 1e3, "o-", ms=3, lw=0.6, color="#e8a39e")
    ax[1].plot(dd, daily.rolling(5, center=True, min_periods=1).mean() / 1e3, color="#c0392b", label="5-day mean")
    ax[1].set(xlabel="Weekday, 2024-2025", ylabel="Daily boardings (thousand)")
    ax[1].legend(frameon=False)
    ax[2].bar(hours, 100 * demand_share, width=1.0, color="#f2c4c0", label="demand")
    ax[2].step(hours, 100 * sqrt_share, where="mid", color="#2c6fb7", lw=2, label="square root")
    ax[2].axhline(100 / len(q), color="gray", ls="--", label="uniform")
    ax[2].set(xlabel="Hour of day", ylabel="Share of departures (%)")
    ax[2].legend(frameon=False)
    fig.suptitle(f"{len(mat)} non-holiday weekdays, Oct 2024-Apr 2025 (same-station records excluded)")
    fig.savefig(OUT / "fig11_observed_demand.png", dpi=150)


if __name__ == "__main__":
    main()
