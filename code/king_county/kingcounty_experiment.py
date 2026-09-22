#!/usr/bin/env python3
"""King County RapidRide: line-total AM boardings → stop OD → Newell checks.

Thinner than Phoenix (no station origins) and BART (no OD / hour profile beyond
a single AM window). Uses GTFS stop sequences as spatial auxiliary information.

Method
  1. Parse monthly directed-route AM (5am–9am) boardings for RapidRide A–H.
  2. For each directed route, take an ordered GTFS stop sequence.
  3. Spread line boardings to stop productions with a declared along-route prior,
     then build a forward-only production-constrained gravity OD on the line.
  4. Experiments (BART Newell analogs):
       - cross-line Newell in a reference month (√boardings vs uniform vs observed f)
       - monthly Newell on system AM RapidRide boardings (Phoenix-style window)

Outputs: code/king_county/output/ and figures/fig_kingcounty_monthly.pdf
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "King_county"
OUT = Path(__file__).resolve().parent / "output"
FIG = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

BOARDINGS = DATA / "average_weekday_boardings_rapidride.csv"
GTFS = DATA / "GTFS"

# Map CSV direction labels to GTFS direction_id using trip headsigns
# (verified against dominant headsign per direction_id).
DIR_MAP = {
    ("A Line", "Northbound"): 1,  # Tukwila Link Station
    ("A Line", "Southbound"): 0,  # Federal Way Transit Center
    ("B Line", "Eastbound"): 0,  # Redmond
    ("B Line", "Westbound"): 1,  # Bellevue
    ("C Line", "Northbound"): 1,  # Downtown Seattle / SLU
    ("C Line", "Southbound"): 0,  # West Seattle Alaska Junction
    ("D Line", "Northbound"): 0,  # Ballard
    ("D Line", "Southbound"): 1,  # Downtown Seattle
    ("E Line", "Northbound"): 0,  # Aurora Village
    ("E Line", "Southbound"): 1,  # Downtown Seattle
    ("F Line", "Eastbound"): 0,  # Renton
    ("F Line", "Westbound"): 1,  # Burien
    ("H Line", "Northbound"): 1,  # Downtown Seattle
    ("H Line", "Southbound"): 0,  # Burien
}


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2 * r * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def load_boardings() -> pd.DataFrame:
    df = pd.read_csv(BOARDINGS)
    df["board"] = pd.to_numeric(
        df["Boardings counts"].astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )
    df["month"] = pd.to_datetime(df["date"] + "-01")
    df = df.dropna(subset=["board"])
    df = df[df["board"] > 0]
    return df[
        [
            "month",
            "date",
            "select_route",
            "select_direction",
            "directed_route",
            "board",
            "weekday_frequency",
        ]
    ].copy()


def build_stop_sequences() -> dict[tuple[str, int], pd.DataFrame]:
    routes = pd.read_csv(GTFS / "routes.txt")
    trips = pd.read_csv(GTFS / "trips.txt")
    st = pd.read_csv(GTFS / "stop_times.txt", dtype={"stop_id": str}, low_memory=False)
    stops = pd.read_csv(GTFS / "stops.txt", dtype={"stop_id": str})
    stop_xy = stops.set_index("stop_id")[["stop_lat", "stop_lon", "stop_name"]]

    rr = routes[routes["route_short_name"].isin([f"{x} Line" for x in "ABCDEFH"])]
    seqs = {}
    for _, r in rr.iterrows():
        name = r["route_short_name"]
        for did in (0, 1):
            cand = trips[(trips.route_id == r.route_id) & (trips.direction_id == did)]
            if cand.empty:
                continue
            # longest unique stop sequence among trips
            best = None
            best_n = -1
            for tid in cand["trip_id"].head(40):
                seq = (
                    st[st.trip_id == tid]
                    .sort_values("stop_sequence")[["stop_id", "stop_sequence"]]
                    .drop_duplicates("stop_id", keep="first")
                )
                if len(seq) > best_n:
                    best_n = len(seq)
                    best = seq
            if best is None or best_n < 3:
                continue
            best = best.merge(stop_xy, left_on="stop_id", right_index=True, how="left")
            best = best.dropna(subset=["stop_lat", "stop_lon"]).reset_index(drop=True)
            best["seq"] = np.arange(len(best))
            seqs[(name, int(did))] = best
    return seqs


def along_route_prior(n: int, kind: str = "midpeak") -> np.ndarray:
    """Declared stop-boarding prior (no land-use file available)."""
    i = (np.arange(n) + 0.5) / n
    if kind == "uniform":
        w = np.ones(n)
    else:
        # slightly higher mid-route, still positive at ends
        w = 0.35 + 0.65 * np.sin(np.pi * i)
    return w / w.sum()


def line_forward_gravity(B: float, lat, lon, beta: float, prior_kind: str = "midpeak"):
    """Spread line boardings to stops; forward-only production-constrained gravity."""
    n = len(lat)
    if n < 3 or B <= 0:
        return None
    # origins 0..n-2, destinations 1..n-1
    w = along_route_prior(n, prior_kind)
    # productions on all but last; attractions on all but first
    P_full = B * w
    P = P_full.copy()
    P[-1] = 0.0
    if P.sum() <= 0:
        return None
    P *= B / P.sum()
    A = P_full.copy()
    A[0] = 0.0
    if A.sum() <= 0:
        return None
    A *= B / A.sum()

    D = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            D[i, j] = haversine_km(lat[i], lon[i], lat[j], lon[j])
    f = np.exp(-beta * D)
    T = np.zeros((n, n))
    for i in range(n - 1):
        if P[i] <= 0:
            continue
        js = np.arange(i + 1, n)
        wj = A[js] * f[i, js]
        s = wj.sum()
        if s <= 0:
            # dump to furthest stop if impedance collapses
            T[i, n - 1] = P[i]
        else:
            T[i, js] = P[i] * wj / s
    return {
        "T": T,
        "P": P,
        "A": A,
        "D": D,
        "boardings_recovered": float(T.sum()),
        "mean_trip_km": float((T * D).sum() / T.sum()) if T.sum() > 0 else np.nan,
        "n_stops": n,
    }


def newell_shares(lam: np.ndarray, n_dep: float) -> dict:
    lam = np.asarray(lam, dtype=float)
    m = len(lam)
    f_u = np.full(m, n_dep / m)
    f_n = n_dep * np.sqrt(lam) / np.sqrt(lam).sum()
    W_u = float(np.sum(lam / (2 * f_u)))
    W_n = float(np.sum(lam / (2 * f_n)))
    return {
        "W_uniform": W_u,
        "W_sqrt": W_n,
        "pct_vs_uniform": 100.0 * (W_u - W_n) / W_u,
        "f_uniform": f_u,
        "f_sqrt": f_n,
    }


def waiting_under_f(lam, f):
    return float(np.sum(lam / (2.0 * np.asarray(f, dtype=float))))


def main():
    board = load_boardings()
    seqs = build_stop_sequences()
    print("stop sequences:", {f"{k[0]} dir{k[1]}": len(v) for k, v in seqs.items()})

    # Impedance: small decay; mean trip length is limited by RapidRide corridor length
    # and the forward-only structure (calibrated check on A Line NB below).
    beta = 0.05
    sample_key = ("A Line", DIR_MAP[("A Line", "Northbound")])
    seq = seqs[sample_key]
    sample_B = float(
        board[(board.select_route == "A Line") & (board.select_direction == "Northbound")]
        .sort_values("month")
        .iloc[-1]
        .board
    )
    out0 = line_forward_gravity(
        sample_B, seq.stop_lat.to_numpy(), seq.stop_lon.to_numpy(), beta
    )
    mean_len = out0["mean_trip_km"]
    print(f"beta={beta:.4f} /km; A-Line NB mean trip km={mean_len:.2f}")

    # Estimate OD for every directed-route × month with a sequence
    od_rows = []
    for _, r in board.iterrows():
        key = (r.select_route, r.select_direction)
        if key not in DIR_MAP:
            continue
        did = DIR_MAP[key]
        seq_key = (r.select_route, did)
        if seq_key not in seqs:
            continue
        seq = seqs[seq_key]
        est = line_forward_gravity(
            float(r.board), seq.stop_lat.to_numpy(), seq.stop_lon.to_numpy(), beta
        )
        if est is None:
            continue
        od_rows.append(
            {
                "date": r.date,
                "month": r.month.strftime("%Y-%m"),
                "route": r.select_route,
                "direction": r.select_direction,
                "directed_route": r.directed_route,
                "boardings": float(r.board),
                "weekday_frequency": int(r.weekday_frequency),
                "n_stops": est["n_stops"],
                "od_total": est["boardings_recovered"],
                "rel_boardings_error": abs(est["boardings_recovered"] - r.board)
                / r.board,
                "mean_trip_km": est["mean_trip_km"],
            }
        )
        # save one example OD matrix
        if r.date == "2023-10" and r.directed_route == "A Line Northbound":
            pd.DataFrame(
                est["T"],
                index=seq.stop_name.fillna(seq.stop_id),
                columns=seq.stop_name.fillna(seq.stop_id),
            ).to_csv(OUT / "od_A_NB_202310.csv")

    od_meta = pd.DataFrame(od_rows)
    od_meta.to_csv(OUT / "line_od_diagnostics.csv", index=False)
    print(
        "OD rows",
        len(od_meta),
        "max rel boarding err",
        od_meta.rel_boardings_error.max(),
        "mean trip km",
        od_meta.mean_trip_km.mean(),
    )

    # --- Cross-line Newell (reference month: 2023-10, complete coverage) ---
    ref = od_meta[od_meta.date == "2023-10"].copy()
    if len(ref) < 8:
        ref = od_meta[od_meta.date == od_meta.date.max()].copy()
    lam = ref["boardings"].to_numpy()
    f_obs = ref["weekday_frequency"].to_numpy(dtype=float)
    n_dep = float(f_obs.sum())  # hold total AM trips/hour across directed routes
    res_sqrt = newell_shares(lam, n_dep)
    W_obs = waiting_under_f(lam, f_obs)
    W_u = waiting_under_f(lam, res_sqrt["f_uniform"])
    W_n = waiting_under_f(lam, res_sqrt["f_sqrt"])
    cross = {
        "ref_month": str(ref.date.iloc[0]),
        "n_directed_routes": int(len(ref)),
        "total_boardings": float(lam.sum()),
        "total_freq": float(n_dep),
        "W_observed_freq": W_obs,
        "W_uniform": W_u,
        "W_sqrt": W_n,
        "pct_sqrt_vs_uniform": 100.0 * (W_u - W_n) / W_u,
        "pct_sqrt_vs_observed": 100.0 * (W_obs - W_n) / W_obs,
        "pct_observed_vs_uniform": 100.0 * (W_u - W_obs) / W_u,
    }
    ref.assign(
        share_demand=lam / lam.sum(),
        f_uniform=res_sqrt["f_uniform"],
        f_sqrt=res_sqrt["f_sqrt"],
        f_observed=f_obs,
    ).to_csv(OUT / "cross_line_newell_refmonth.csv", index=False)

    # --- Monthly Newell on system AM RapidRide boardings ---
    monthly = (
        od_meta.groupby("month", as_index=False)["boardings"]
        .sum()
        .sort_values("month")
    )
    monthly.to_csv(OUT / "monthly_system_boardings.csv", index=False)
    # recovery-style window overlapping Phoenix narrative
    win = monthly[(monthly.month >= "2020-04") & (monthly.month <= "2024-05")]
    y2019 = monthly[(monthly.month >= "2019-06") & (monthly.month <= "2019-12")]
    # data start mid-2019
    res_win = newell_shares(win.boardings.to_numpy(), n_dep=float(len(win)))
    res_2019 = newell_shares(y2019.boardings.to_numpy(), n_dep=float(len(y2019)))

    summary = {
        "beta_per_km": beta,
        "n_directed_route_sequences": len(seqs),
        "od_estimation_rows": int(len(od_meta)),
        "max_rel_boardings_error": float(od_meta.rel_boardings_error.max()),
        "mean_trip_km_avg": float(od_meta.mean_trip_km.mean()),
        "cross_line_newell": cross,
        "monthly_window": "2020-04_to_2024-05",
        "monthly_n": int(len(win)),
        "monthly_pct_sqrt_vs_uniform": res_win["pct_vs_uniform"],
        "y2019_partial_pct_sqrt_vs_uniform": res_2019["pct_vs_uniform"],
        "note": "Boardings are AM-peak (5am–9am) average weekday directed-route totals. "
        "Stop OD uses GTFS sequences + mid-peak prior + forward gravity; not surveyed OD.",
    }
    (OUT / "experiment_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # Figure
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, axes = plt.subplots(2, 1, figsize=(8.2, 5.4))
    ax = axes[0]
    t = pd.to_datetime(monthly.month)
    ax.plot(t, monthly.boardings / 1000.0, color="#1f4e79", lw=1.4)
    ax.axvspan(
        pd.Timestamp("2020-04-01"),
        pd.Timestamp("2024-05-31"),
        color="#c6d9f1",
        alpha=0.45,
        label="Monthly Newell window",
    )
    ax.set_ylabel("AM RapidRide boardings (thousands)")
    ax.set_title("King County Metro RapidRide: sum of directed-route AM boardings")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    # cross-line bars for ref month
    lab = [re.sub(r" Line ", "\n", d) for d in ref.directed_route]
    x = np.arange(len(ref))
    w = 0.25
    ax.bar(x - w, f_obs / n_dep, width=w, label="Observed freq share", color="#d62728")
    ax.bar(x, res_sqrt["f_uniform"] / n_dep, width=w, label="Uniform", color="#7f7f7f")
    ax.bar(
        x + w,
        res_sqrt["f_sqrt"] / n_dep,
        width=w,
        label="Square-root",
        color="#2ca02c",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(lab, fontsize=7)
    ax.set_ylabel("Share of AM trips")
    ax.set_title(
        f"Cross-line Newell ({cross['ref_month']}): "
        f"√λ cuts waiting {cross['pct_sqrt_vs_uniform']:.1f}% vs uniform, "
        f"{cross['pct_sqrt_vs_observed']:.1f}% vs observed frequencies"
    )
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig_kingcounty_monthly.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_kingcounty_monthly.pdf", bbox_inches="tight")
    print("wrote", FIG / "fig_kingcounty_monthly.pdf")


if __name__ == "__main__":
    main()
