#!/usr/bin/env python3
"""Phoenix monthly OD estimation and Newell-style monthly adaptivity experiment.

Data limits relative to BART:
  - origins = monthly station boardings only (no destinations, no hour-of-day)
  - network = Valley Metro Rail GTFS/GMNS snapshot

Method:
  1. Parse FY09--present monthly boardings by light-rail station.
  2. Match stations to GTFS coordinates (directional EB/WB pairs averaged).
  3. Each month: production-constrained gravity OD
        T_{od} = P_o * A_d f(c_{od}) / sum_k A_k f(c_{ok}),
     with A_d = P_d (boardings as attraction proxy), f(c)=exp(-beta * km), T_{oo}=0.
  4. Monthly Newell check (BART Sec.7 analog at month grain): fixed total
     departures over a window of months, uniform vs square-root allocation.

Outputs under code/phoenix/output/ and figures/fig_phoenix_monthly.pdf.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "Phoenix"
OUT = Path(__file__).resolve().parent / "output"
FIG = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

BOARDINGS_XLSX = DATA / "boardings-by-station-database---fy09-to-present-1738184335.xlsx"
GTFS_STOPS = DATA / "GTFS" / "stops.txt"

# Manual aliases when automatic match fails (Valley Metro Rail naming)
ALIASES = {
    "metro parkway": "metro pkwy",
    "mountain view/ 25th ave": "mountain view/25th ave",
    "25th ave/ dunlap": "25th ave/dunlap",
    "wb van buren/central ave": "van buren/central ave",
    "eb van buren/1st ave": "van buren/1st ave",
    "eb jefferson/1st ave": "jefferson/1st ave",
    "wb washington/central ave": "washington/central ave",
    "eb 3rd st/jefferson": "3rd st/jefferson",
    "wb 3rd st/washington": "3rd st/washington",
    "wb 12th st/washington": "12th st/washington",
    "eb 12th st/jefferson": "12th st/jefferson",
    "eb 24th st/jefferson": "24th st/jefferson",
    "wb 24th st/washington": "24th st/washington",
    "center pkwy/washington st": "center pkwy/washington",
    "mill ave/third st": "mill ave/3rd st",
    "university dr/rural": "university/rural",
    "price101 fwy/apache blvd": "price101/apache blvd",
    "price-101 fwy/apache blvd": "price101/apache blvd",
    "stapley/main st": "stapley dr/main st",
    "dorsey/apache blvd": "dorsey ln/apache blvd",
    "mcclintock/apache blvd": "mcclintock dr/apache blvd",
}

# Approximate WGS84 for northwest-extension stations absent from the 2023 GTFS snapshot
MANUAL_COORDS = {
    "Mountain View/ 25th Ave": (33.5675, -112.1110),
    "25th Ave/ Dunlap": (33.5672, -112.1115),
}


def norm(s: str) -> str:
    s = str(s).lower().strip()
    s = s.replace("&", "/")
    for a, b in [
        ("avenue", "ave"),
        ("street", "st"),
        ("drive", "dr"),
        ("boulevard", "blvd"),
        ("parkway", "pkwy"),
        ("freeway", "fwy"),
    ]:
        s = s.replace(a, b)
    s = re.sub(r"\b(eb|wb|nb|sb)\b", "", s)
    s = re.sub(r"\btc\b", "", s)
    s = re.sub(r"[^a-z0-9/ ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*/\s*", "/", s)
    return ALIASES.get(s, s)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def load_boardings() -> tuple[pd.DataFrame, list[str]]:
    raw = pd.read_excel(BOARDINGS_XLSX, header=None)
    dates = []
    for j in range(1, raw.shape[1]):
        v = raw.iloc[2, j]
        if pd.notna(v) and not isinstance(v, str):
            dates.append(pd.Timestamp(v))
        else:
            dates.append(pd.NaT)
    # light-rail stations: rows 3..48 inclusive (exclude system totals at 49+)
    names = [str(raw.iloc[i, 0]).strip() for i in range(3, 49)]
    mat = []
    for i in range(3, 49):
        row = []
        for j, d in enumerate(dates, start=1):
            v = raw.iloc[i, j]
            try:
                fv = float(v)
                row.append(fv if np.isfinite(fv) else np.nan)
            except (TypeError, ValueError):
                row.append(np.nan)
        mat.append(row)
    df = pd.DataFrame(mat, index=names, columns=dates)
    df = df.loc[:, ~df.columns.isna()]
    # collapse duplicate month stamps if present
    if df.columns.duplicated().any():
        df = df.T.groupby(level=0).mean().T
    return df, names


def match_coordinates(names: list[str]) -> pd.DataFrame:
    stops = pd.read_csv(GTFS_STOPS)
    buckets: dict[str, list[tuple[float, float, str]]] = {}
    for _, r in stops.iterrows():
        key = norm(r["stop_name"])
        buckets.setdefault(key, []).append((float(r["stop_lat"]), float(r["stop_lon"]), r["stop_name"]))
        # also store without spaces around /
        buckets.setdefault(key.replace(" ", ""), []).append(
            (float(r["stop_lat"]), float(r["stop_lon"]), r["stop_name"])
        )

    rows = []
    for name in names:
        key = norm(name)
        hits = buckets.get(key) or buckets.get(key.replace(" ", ""))
        if not hits:
            parts = [p for p in key.split("/") if p]
            if len(parts) == 2:
                hits = buckets.get(f"{parts[1]}/{parts[0]}") or buckets.get(
                    f"{parts[0]}/{parts[1]}"
                )
            if not hits and len(parts) >= 1:
                cands = [
                    (k, v)
                    for k, v in buckets.items()
                    if all(p in k for p in parts) and len(v) > 0
                ]
                # prefer shortest key
                if cands:
                    cands.sort(key=lambda kv: len(kv[0]))
                    hits = cands[0][1]
        if not hits:
            rows.append({"station": name, "lat": np.nan, "lon": np.nan, "gtfs": None, "ok": False})
            continue
        lat = float(np.mean([h[0] for h in hits]))
        lon = float(np.mean([h[1] for h in hits]))
        rows.append(
            {
                "station": name,
                "lat": lat,
                "lon": lon,
                "gtfs": hits[0][2],
                "ok": True,
            }
        )
    df = pd.DataFrame(rows)
    for name, (la, lo) in MANUAL_COORDS.items():
        m = df["station"] == name
        if m.any() and not bool(df.loc[m, "ok"].iloc[0]):
            df.loc[m, ["lat", "lon", "gtfs", "ok"]] = [la, lo, "manual_extension", True]
    return df


def gravity_od(P: np.ndarray, D: np.ndarray, beta: float) -> np.ndarray:
    """Production-constrained gravity; attractions = P; impedance exp(-beta*km)."""
    P = np.asarray(P, dtype=float).reshape(-1)
    n = len(P)
    f = np.exp(-beta * D)
    np.fill_diagonal(f, 0.0)
    A = P.copy()
    T = np.zeros((n, n))
    for o in range(n):
        if float(P[o]) <= 0:
            continue
        w = A * f[o]
        s = float(w.sum())
        if s <= 0:
            continue
        T[o] = float(P[o]) * w / s
    return T


def newell_monthly(lam: np.ndarray, n_dep: float) -> dict:
    """Fixed total departures over months: uniform vs square-root shares; waiting ~ sum lam/(2f)."""
    lam = np.asarray(lam, dtype=float)
    m = len(lam)
    # continuous Newell with priced? Use fixed-envelope form like Sec.4 partition / intro Newell
    # waiting under frequency density: J = (c0/2) * sum_r (lam_r / f_r) with sum f = n_dep, stage length=1 month unit
    # optimal f_r ∝ sqrt(lam_r); uniform f_r = n_dep/m
    f_u = np.full(m, n_dep / m)
    f_n = n_dep * np.sqrt(lam) / np.sqrt(lam).sum()
    # passenger-month waiting units (c0=1): lam/(2f) per month
    W_u = float(np.sum(lam / (2 * f_u)))
    W_n = float(np.sum(lam / (2 * f_n)))
    # continuous Newell limit for comparison
    S = float(np.sum(np.sqrt(lam)))
    W_star = (S ** 2) / (2 * n_dep)
    return {
        "W_uniform": W_u,
        "W_sqrt": W_n,
        "W_star": W_star,
        "pct_vs_uniform": 100.0 * (W_u - W_n) / W_u,
        "pct_star_vs_uniform": 100.0 * (W_u - W_star) / W_u,
        "f_uniform": f_u,
        "f_sqrt": f_n,
    }


def main():
    board, names = load_boardings()
    coords = match_coordinates(names)
    coords.to_csv(OUT / "station_coordinate_match.csv", index=False)
    n_ok = int(coords["ok"].sum())
    print(f"matched stations: {n_ok}/{len(names)}")
    if n_ok < 30:
        raise SystemExit("too few station matches")

    # Restrict to matched stations with coordinates
    ok_names = coords.loc[coords.ok, "station"].tolist()
    board = board.loc[ok_names]
    lat = coords.set_index("station").loc[ok_names, "lat"].to_numpy()
    lon = coords.set_index("station").loc[ok_names, "lon"].to_numpy()
    n = len(ok_names)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            D[i, j] = haversine_km(lat[i], lon[i], lat[j], lon[j])

    # Calibrate beta so mean trip length ~ 8 km under a reference month
    # Prefer a mid-recovery month with complete station coverage
    ref = None
    for cand in board.columns:
        if cand.year == 2023 and cand.month == 10:
            ref = cand
            break
    if ref is None:
        ref = board.columns[-13]
    P_ref = board[ref].fillna(0).to_numpy(dtype=float).reshape(-1)
    active = P_ref > 0
    beta = 0.20  # /km initial
    for _ in range(8):
        T = gravity_od(P_ref, D, beta)
        trips = T.sum()
        mean_len = (T * D).sum() / trips if trips > 0 else 8.0
        # adjust beta toward 8 km mean
        if mean_len > 9.0:
            beta *= 1.15
        elif mean_len < 7.0:
            beta *= 0.87
        else:
            break
    print(f"beta={beta:.4f} /km; ref month {ref.date()}; mean trip km={mean_len:.2f}")

    # Estimate OD for each month with enough active stations
    months = [c for c in board.columns if c >= pd.Timestamp("2019-01-01")]
    records = []
    od_stack = {}
    for m in months:
        P = board[m].fillna(0).to_numpy(float)
        if (P > 0).sum() < 20:
            continue
        T = gravity_od(P, D, beta)
        origin_err = float(np.max(np.abs(T.sum(1) - P) / np.maximum(P, 1.0)))
        records.append(
            {
                "month": m.strftime("%Y-%m"),
                "system_boardings": float(P.sum()),
                "n_active_stations": int((P > 0).sum()),
                "od_total": float(T.sum()),
                "max_rel_origin_error": origin_err,
                "mean_trip_km": float((T * D).sum() / T.sum()) if T.sum() > 0 else np.nan,
            }
        )
        od_stack[m.strftime("%Y-%m")] = T
    od_meta = pd.DataFrame(records)
    od_meta.to_csv(OUT / "monthly_od_diagnostics.csv", index=False)

    # Save one example OD (Oct 2023)
    key = "2023-10" if "2023-10" in od_stack else od_meta["month"].iloc[-1]
    T_ex = od_stack[key]
    pd.DataFrame(T_ex, index=ok_names, columns=ok_names).to_csv(OUT / f"od_{key.replace('-', '')}.csv")

    # Monthly Newell experiment on system boardings (2019-01 .. 2024-12)
    series = od_meta.set_index("month")["system_boardings"]
    # pandemic recovery window used in narrative: 2020-04 through 2024-06
    win = series.loc["2020-04":"2024-06"]
    n_dep = float(len(win))  # one "departure unit" per month under uniform
    # scale: treat n_dep as total relative service-months (= number of months)
    res = newell_monthly(win.to_numpy(), n_dep=n_dep)
    # also report with larger envelope (like denser service): n_dep = 3 * n_months
    res3 = newell_monthly(win.to_numpy(), n_dep=3 * n_dep)

    # Pre-pandemic baseline year 2019 for depth comparison
    y2019 = series.loc["2019-01":"2019-12"]
    res2019 = newell_monthly(y2019.to_numpy(), n_dep=float(len(y2019)))

    summary = {
        "n_stations_matched": n_ok,
        "beta_per_km": beta,
        "ref_month": str(ref.date()),
        "ref_mean_trip_km": mean_len,
        "window": "2020-04_to_2024-06",
        "n_months_window": int(len(win)),
        "newell_pct_saving_vs_uniform": res["pct_vs_uniform"],
        "newell_star_pct_saving_vs_uniform": res["pct_star_vs_uniform"],
        "newell_pct_saving_3x_envelope": res3["pct_vs_uniform"],
        "year2019_pct_saving_vs_uniform": res2019["pct_vs_uniform"],
        "W_uniform_window": res["W_uniform"],
        "W_sqrt_window": res["W_sqrt"],
        "note": "Waiting units are relative under monthly stage lengths=1 and c0=1; "
        "n_dep equals the number of months (unit service intensity per month under uniform).",
    }
    (OUT / "experiment_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # Shares table for figure/table
    shares = pd.DataFrame(
        {
            "month": win.index,
            "boardings": win.to_numpy(),
            "share_uniform": 1.0 / len(win),
            "share_sqrt": res["f_sqrt"] / res["f_sqrt"].sum(),
            "share_demand": win.to_numpy() / win.to_numpy().sum(),
        }
    )
    shares.to_csv(OUT / "monthly_newell_shares.csv", index=False)

    # Figure
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib missing; skip figure")
        return

    fig, axes = plt.subplots(2, 1, figsize=(8.2, 5.2), sharex=False)
    ax = axes[0]
    full = series.loc["2019-01":]
    ax.plot(pd.to_datetime(full.index), full.values / 1000.0, color="#1f4e79", lw=1.4)
    ax.axvspan(pd.Timestamp("2020-04-01"), pd.Timestamp("2024-06-30"), color="#c6d9f1", alpha=0.45, label="Newell window")
    ax.set_ylabel("System boardings (thousands)")
    ax.set_title("Valley Metro Rail: monthly station-sum boardings")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    x = np.arange(len(shares))
    ax.plot(x, shares["share_demand"], label="Demand share", color="#7f7f7f", lw=1.2)
    ax.plot(x, shares["share_uniform"], label="Uniform service share", color="#d62728", ls="--", lw=1.2)
    ax.plot(x, shares["share_sqrt"], label="Square-root service share", color="#2ca02c", lw=1.4)
    ax.set_ylabel("Share")
    ax.set_xlabel("Month in window (2020-04 to 2024-06)")
    ax.set_title(
        f"Monthly Newell allocation: square-root cuts modeled waiting by {res['pct_vs_uniform']:.1f}% vs uniform"
    )
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig_phoenix_monthly.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_phoenix_monthly.pdf", bbox_inches="tight")
    print("wrote", FIG / "fig_phoenix_monthly.pdf")


if __name__ == "__main__":
    main()
