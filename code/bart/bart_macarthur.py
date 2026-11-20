"""MacArthur morning retiming check (Section 7.2, Figure 12, Table 10 note c).

Inputs: observed mean weekday boardings at MacArthur (origin == "MCAR", all
destinations except MCAR itself, all lines and directions pooled), hours
05..08, over the 123 weekdays of bart_observed_demand.py.
Paper: 33.9, 115.9, 306.2, 525.7 pax/h.

Model (the paper's "every departure carries everyone waiting" assumption):
arrivals are uniform within each hour, so cumulative arrivals A(t) are
piecewise linear; 24 departures in 05:00-09:00 (10-minute headway), the last
at 09:00.  Waiting between departures d_{k-1} and d_k is the area
int (A(t) - A(d_{k-1})) dt.
  * uniform:      d_k = 05:00 + 10k min                        -> 81.8 pax-h
  * square root:  d_k solves F(d_k) = k, F(t) = 24 int sqrt(lambda) / int_0^4h sqrt(lambda)
                                                                -> 66.7 pax-h (-18.4%)
  * exact optimum on a 1-minute grid (DP over departure times) -> 66.2 pax-h
  * continuum:    W = sum_h lambda_h/(2 f_h), f_h = 6/h (uniform) or
                  24 sqrt(lambda_h)/sum sqrt(lambda) (square root)  -> 17.2% saving

Ported from the earlier independent check
  scratchpad/urt_review/mathcheck/macarthur.py (math_check.md, Section 2),
with exact (closed-form) integration in place of midpoint quadrature.

Run from the repository root:
    python -I code/bart/bart_macarthur.py [--station MCAR] [--use-paper-rates]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OD_TD = ROOT / "data" / "BART" / "GMNS" / "OD_demand_td.csv"
OUT = Path(__file__).resolve().parent / "output"
PAPER_RATES = [33.9, 115.9, 306.2, 525.7]
N_DEP = 24
T_END = 4.0  # hours after 05:00


def station_rates(station: str, hours=(5, 6, 7, 8)) -> np.ndarray:
    df = pd.read_csv(OD_TD, usecols=["date", "hour", "day_type", "origin", "destination", "volume"])
    wk = df[(df.day_type == "Weekday") & (df.origin != df.destination)]
    n_days = wk.date.nunique()
    s = wk[wk.origin == station].groupby("hour").volume.sum() / n_days
    return s.reindex(list(hours), fill_value=0).to_numpy(dtype=float)


class Arrivals:
    """Piecewise-constant hourly rates -> A(t), int_0^t A, both exact."""

    def __init__(self, lam):
        self.lam = np.asarray(lam, dtype=float)
        self.cumA = np.concatenate([[0.0], np.cumsum(self.lam)])            # A at hour marks
        self.cumI = np.concatenate([[0.0], np.cumsum(self.cumA[:-1] + self.lam / 2)])  # int A at marks

    def A(self, t):
        t = np.clip(t, 0, len(self.lam))
        h = np.minimum(np.floor(t).astype(int), len(self.lam) - 1)
        return self.cumA[h] + self.lam[h] * (t - h)

    def IA(self, t):
        t = np.clip(t, 0, len(self.lam))
        h = np.minimum(np.floor(t).astype(int), len(self.lam) - 1)
        r = t - h
        return self.cumI[h] + self.cumA[h] * r + self.lam[h] * r * r / 2

    def wait(self, deps) -> float:
        """Event-based waiting (pax-h) when each departure clears the platform."""
        d = np.concatenate([[0.0], np.asarray(deps, dtype=float)])
        a, b = d[:-1], d[1:]
        return float(np.sum(self.IA(b) - self.IA(a) - self.A(a) * (b - a)))


def sqrt_departures(lam, n=N_DEP) -> np.ndarray:
    root = np.sqrt(np.asarray(lam, dtype=float))
    F = np.concatenate([[0.0], np.cumsum(root)]) * n / root.sum()
    out = []
    for k in range(1, n + 1):
        h = int(np.searchsorted(F, k, side="left")) - 1
        h = min(max(h, 0), len(root) - 1)
        out.append(h + (k - F[h]) / (F[h + 1] - F[h]))
    return np.array(out)


def grid_optimum(arr: Arrivals, n=N_DEP, step_min=1):
    """Exact DP: n departures on a step_min grid, last departure at 09:00."""
    m = int(round(T_END * 60 / step_min))
    t = np.arange(m + 1) * step_min / 60.0
    A, I = arr.A(t), arr.IA(t)
    # seg[a, b] = waiting between departures at grid a < b
    seg = (I[None, :] - I[:, None]) - A[:, None] * (t[None, :] - t[:, None])
    seg[np.tril_indices(m + 1)] = np.inf
    best = np.full(m + 1, np.inf); best[0] = 0.0
    arg = np.zeros((n + 1, m + 1), dtype=int)
    for k in range(1, n + 1):
        tot = best[:, None] + seg
        arg[k] = np.argmin(tot, axis=0)
        best = tot[arg[k], np.arange(m + 1)]
    deps, b = [], m
    for k in range(n, 0, -1):
        deps.append(b); b = arg[k, b]
    return float(best[m]), t[np.array(deps[::-1])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--station", default="MCAR")
    ap.add_argument("--use-paper-rates", action="store_true", help="skip the data and use the rounded paper rates")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    lam = np.array(PAPER_RATES) if args.use_paper_rates else station_rates(args.station)
    arr = Arrivals(lam)
    uni = np.arange(1, N_DEP + 1) * T_END / N_DEP
    sq = sqrt_departures(lam)
    W_u, W_s = arr.wait(uni), arr.wait(sq)
    W_opt, opt = grid_optimum(arr)
    # continuum: hour h gets f_h departures/h; W = sum lambda_h / (2 f_h)
    f_u = np.full(4, N_DEP / T_END)
    f_s = N_DEP * np.sqrt(lam) / np.sqrt(lam).sum()
    C_u, C_s = float(np.sum(lam / (2 * f_u))), float(np.sum(lam / (2 * f_s)))
    res = {
        "station": args.station, "rates_pax_per_h_05_08": [round(x, 2) for x in lam],
        "uniform_event_pax_h": W_u, "uniform_avg_wait_min": 60 * W_u / lam.sum(),
        "sqrt_event_pax_h": W_s, "sqrt_event_saving": 1 - W_s / W_u,
        "grid1min_optimum_pax_h": W_opt, "grid_optimum_saving": 1 - W_opt / W_u,
        "continuum_uniform_pax_h": C_u, "continuum_sqrt_pax_h": C_s, "continuum_saving": 1 - C_s / C_u,
        "sqrt_departures_hhmm": [f"{5 + int(x)}:{int(round((x % 1) * 60)):02d}" for x in sq],
    }
    (OUT / f"macarthur_{args.station}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"{args.station} rates 05-08: {', '.join(f'{x:.1f}' for x in lam)}  (paper 33.9, 115.9, 306.2, 525.7)")
    print(f"uniform event-based  {W_u:.2f} pax-h, avg wait {res['uniform_avg_wait_min']:.2f} min  (paper 81.8, 5.0)")
    print(f"sqrt event-based     {W_s:.2f} pax-h, saving {100*res['sqrt_event_saving']:.2f}%  (paper 66.7, 18.4%)")
    print(f"1-min grid optimum   {W_opt:.2f} pax-h  (paper 66.2)")
    print(f"continuum            {C_u:.2f} -> {C_s:.2f} pax-h, saving {100*res['continuum_saving']:.2f}%  (paper 17.2%)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    tt = np.linspace(0, T_END, 961)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True, constrained_layout=True)
    for ax, deps, W, title in [(axes[0], uni, W_u, "(a) Uniform 10-minute dispatch"),
                               (axes[1], sq, W_s, "(b) Square-root dispatch")]:
        D = np.array([arr.A(deps[deps <= x].max()) if (deps <= x).any() else 0.0 for x in tt])
        ax.plot(5 + tt, arr.A(tt), color="#c0392b", lw=2, label="cumulative arrivals A(t)")
        ax.step(5 + tt, D, where="post", color="#2c6fb7", ls="--", label="cumulative boardings D(t)")
        ax.fill_between(5 + tt, D, arr.A(tt), color="#f5deb3", step=None)
        ax.set_title(f"{title}\nwaiting = {W:.1f} passenger-hours", loc="left")
        ax.set_xlabel("time of day (h)")
    axes[0].set_ylabel("cumulative passengers"); axes[0].legend(frameon=False, loc="center left")
    fig.savefig(OUT / f"fig12_macarthur_{args.station}.png", dpi=150)


if __name__ == "__main__":
    main()
