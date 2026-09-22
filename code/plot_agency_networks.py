#!/usr/bin/env python3
"""Draw Phoenix and King County network maps in the style of fig_bart_network.pdf.

Style cues from the BART figure:
  - white background, no axes
  - thick colored service lines
  - white station disks with thin black edge
  - dark-navy serif labels on terminals / hubs only
  - legend of colored lines at lower left
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

LABEL_COLOR = "#1a3a6e"
STATION_EDGE = "#222222"
LW = 3.8
STATION_R = 0.00115  # relative to data units; overridden per map


def _setup_ax(ax):
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_visible(False)


def _draw_polyline(ax, lon, lat, color, lw=LW, z=2, alpha=1.0):
    if len(lon) < 2:
        return
    ax.plot(lon, lat, color=color, lw=lw, solid_capstyle="round", solid_joinstyle="round", zorder=z, alpha=alpha)


def _stations(ax, lon, lat, s=28, z=5):
    ax.scatter(
        lon,
        lat,
        s=s,
        facecolors="white",
        edgecolors=STATION_EDGE,
        linewidths=0.9,
        zorder=z,
    )


def _label(ax, x, y, text, dx=0.0, dy=0.0, ha="left", va="bottom", size=9):
    t = ax.text(
        x + dx,
        y + dy,
        text,
        color=LABEL_COLOR,
        fontsize=size,
        fontfamily="serif",
        fontweight="bold",
        ha=ha,
        va=va,
        zorder=6,
    )
    t.set_path_effects(
        [pe.withStroke(linewidth=3.0, foreground="white")]
    )


def _legend(ax, items, loc="lower left"):
    handles = [
        Line2D([0], [0], color=c, lw=3.2, solid_capstyle="round", label=name)
        for name, c in items
    ]
    leg = ax.legend(
        handles=handles,
        loc=loc,
        frameon=False,
        fontsize=9,
        labelcolor=LABEL_COLOR,
        prop={"family": "serif", "size": 9},
        handlelength=1.6,
        borderaxespad=0.4,
    )
    return leg


def _longest_shape(trips, shapes, route_id, direction_id=None):
    """Return (lon, lat) arrays for the longest shape of a route(/direction)."""
    cand = trips[trips.route_id == route_id]
    if direction_id is not None and "direction_id" in cand.columns:
        cand = cand[cand.direction_id == direction_id]
    if cand.empty:
        return None
    best = None
    best_n = -1
    for sid in cand["shape_id"].dropna().unique():
        g = shapes[shapes.shape_id == sid].sort_values("shape_pt_sequence")
        if len(g) > best_n:
            best_n = len(g)
            best = g
    if best is None:
        return None
    return best["shape_pt_lon"].to_numpy(), best["shape_pt_lat"].to_numpy()


def _offset_polyline(lon, lat, meters):
    """Perpendicular offset in approx meters (local equirectangular)."""
    lon = np.asarray(lon, float)
    lat = np.asarray(lat, float)
    if len(lon) < 2:
        return lon, lat
    mid_lat = np.nanmean(lat)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(mid_lat))
    x = lon * m_per_deg_lon
    y = lat * m_per_deg_lat
    dx = np.diff(x, prepend=x[0])
    dy = np.diff(y, prepend=y[0])
    dx[0] = dx[1] if len(dx) > 1 else 0.0
    dy[0] = dy[1] if len(dy) > 1 else 0.0
    # smooth tangent
    tx = np.convolve(dx, np.ones(5) / 5, mode="same")
    ty = np.convolve(dy, np.ones(5) / 5, mode="same")
    norm = np.hypot(tx, ty)
    norm = np.where(norm < 1e-6, 1.0, norm)
    ux, uy = -ty / norm, tx / norm
    x2 = x + ux * meters
    y2 = y + uy * meters
    return x2 / m_per_deg_lon, y2 / m_per_deg_lat


# ---------------------------------------------------------------------------
# Phoenix
# ---------------------------------------------------------------------------

def plot_phoenix():
    data = ROOT / "data" / "Phoenix"
    stations = pd.read_csv(ROOT / "code" / "phoenix" / "output" / "station_coordinate_match.csv")
    trips = pd.read_csv(data / "GTFS" / "trips.txt")
    shapes = pd.read_csv(data / "GTFS" / "shapes.txt")
    st = pd.read_csv(
        data / "GTFS" / "stop_times.txt",
        dtype={"stop_id": str},
        usecols=["trip_id", "stop_id", "stop_sequence"],
        low_memory=False,
    )
    stops = pd.read_csv(data / "GTFS" / "stops.txt", dtype={"stop_id": str})

    # Full east–west corridor shape (Dunlap ↔ Gilbert)
    xy = _longest_shape(trips, shapes, "RAIL", direction_id=None)
    # Prefer the full 38-stop Dunlap–Gilbert pattern
    rail = trips[trips.route_id == "RAIL"]
    full = rail[rail.trip_headsign == "Gilbert Rd/Main St"]
    best = None
    best_n = -1
    for sid in full["shape_id"].unique():
        g = shapes[shapes.shape_id == sid].sort_values("shape_pt_sequence")
        if len(g) > best_n:
            best_n = len(g)
            best = g
    lon = best["shape_pt_lon"].to_numpy()
    lat = best["shape_pt_lat"].to_numpy()

    # NW extension stub: connect Metro Parkway / Mountain View to 19th Ave/Dunlap
    nw = stations[stations.station.isin(["Metro Parkway", "Mountain View/ 25th Ave", "25th Ave/ Dunlap", "19th Ave/Dunlap"])]
    nw = nw.set_index("station").loc[
        ["Metro Parkway", "Mountain View/ 25th Ave", "25th Ave/ Dunlap", "19th Ave/Dunlap"]
    ]

    # Brand teal for Valley Metro Rail
    rail_color = "#00A3A1"

    fig, ax = plt.subplots(figsize=(7.2, 5.6), dpi=200)
    _setup_ax(ax)

    _draw_polyline(ax, lon, lat, rail_color, lw=LW, z=2)
    _draw_polyline(ax, nw["lon"].to_numpy(), nw["lat"].to_numpy(), rail_color, lw=LW, z=2)

    _stations(ax, stations["lon"], stations["lat"], s=22)

    # Labels: terminals + a few hubs (BART-style sparse labeling)
    labels = {
        "Metro Parkway": dict(dx=-0.012, dy=0.006, ha="right", va="bottom"),
        "19th Ave/Dunlap": dict(dx=-0.022, dy=0.0, ha="right", va="center"),
        "Central Ave/Camelback": dict(dx=0.006, dy=0.008, ha="left", va="bottom"),
        "WB Van Buren/Central Ave": dict(dx=-0.014, dy=-0.004, ha="right", va="center"),
        "44th St/Washington": dict(dx=0.0, dy=0.01, ha="center", va="bottom"),
        "Mill Ave/Third St": dict(dx=0.022, dy=0.018, ha="left", va="bottom"),
        "Gilbert Rd/Main St": dict(dx=0.006, dy=0.004, ha="left", va="bottom"),
    }
    short = {
        "Metro Parkway": "Metro Parkway",
        "19th Ave/Dunlap": "19th Ave/Dunlap",
        "Central Ave/Camelback": "Camelback/Central",
        "WB Van Buren/Central Ave": "Downtown Phoenix",
        "44th St/Washington": "44th St/Washington",
        "Mill Ave/Third St": "Mill Ave (Tempe)",
        "Gilbert Rd/Main St": "Gilbert Rd/Main St",
    }
    by = stations.set_index("station")
    for name, sty in labels.items():
        if name not in by.index:
            continue
        r = by.loc[name]
        _label(ax, r.lon, r.lat, short[name], **sty, size=8.5)

    _legend(ax, [("Valley Metro Rail", rail_color)], loc="lower left")

    # Padding
    pad_x = 0.02
    pad_y = 0.015
    ax.set_xlim(stations.lon.min() - pad_x, stations.lon.max() + pad_x)
    ax.set_ylim(stations.lat.min() - pad_y, stations.lat.max() + pad_y)

    fig.tight_layout(pad=0.2)
    out = FIG / "fig_phoenix_network.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(FIG / "fig_phoenix_network.png", bbox_inches="tight", pad_inches=0.08, dpi=200)
    plt.close(fig)
    print("wrote", out)
    return out


# ---------------------------------------------------------------------------
# King County RapidRide
# ---------------------------------------------------------------------------

# Official-ish RapidRide brand colors
RR_COLORS = {
    "A Line": "#00A651",
    "B Line": "#E31C23",
    "C Line": "#00AEEF",
    "D Line": "#7C2D8E",
    "E Line": "#F7941D",
    "F Line": "#8DC63F",
    "H Line": "#00A99D",
}

# Terminal / hub labels per line (one direction's endpoints)
RR_LABELS = {
    "A Line": [
        ("Federal Way TC", 0),
        ("Tukwila Intl Blvd", 1),
    ],
    "B Line": [
        ("Bellevue TC", 1),
        ("Redmond TC", 0),
    ],
    "C Line": [
        ("West Seattle", 0),
        ("South Lake Union", 1),
    ],
    "D Line": [
        ("Ballard", 0),
        ("Downtown Seattle", 1),
    ],
    "E Line": [
        ("Aurora Village", 0),
        ("Downtown Seattle", 1),
    ],
    "F Line": [
        ("Burien TC", 1),
        ("Renton", 0),
    ],
    "H Line": [
        ("Burien TC", 0),
        ("Downtown Seattle", 1),
    ],
}


def _rapidride_sequences():
    """Reuse the experiment's stop-sequence builder logic inline."""
    gtfs = ROOT / "data" / "King_county" / "GTFS"
    routes = pd.read_csv(gtfs / "routes.txt")
    trips = pd.read_csv(gtfs / "trips.txt")
    st = pd.read_csv(gtfs / "stop_times.txt", dtype={"stop_id": str}, low_memory=False)
    stops = pd.read_csv(gtfs / "stops.txt", dtype={"stop_id": str})
    stop_xy = stops.set_index("stop_id")[["stop_lat", "stop_lon", "stop_name"]]
    shapes = pd.read_csv(gtfs / "shapes.txt")

    rr = routes[routes["route_short_name"].isin([f"{x} Line" for x in "ABCDEFH"])]
    out = {}
    for _, r in rr.iterrows():
        name = r["route_short_name"]
        # Prefer direction 0 shape as the drawn geometry (undirected map)
        xy = _longest_shape(trips, shapes, r.route_id, direction_id=0)
        if xy is None:
            xy = _longest_shape(trips, shapes, r.route_id, direction_id=None)
        # Station sequence for markers: longest trip dir 0
        cand = trips[(trips.route_id == r.route_id) & (trips.direction_id == 0)]
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
        if best is None:
            continue
        best = best.merge(stop_xy, left_on="stop_id", right_index=True, how="left")
        best = best.dropna(subset=["stop_lat", "stop_lon"]).reset_index(drop=True)
        out[name] = {"lon": xy[0], "lat": xy[1], "stops": best, "route_id": r.route_id}
    return out


def plot_king_county():
    nets = _rapidride_sequences()
    # Slight parallel offsets so downtown overlaps remain readable (BART-style)
    # Order offsets by a stable line order
    order = ["A Line", "B Line", "C Line", "D Line", "E Line", "F Line", "H Line"]
    offsets_m = {
        "A Line": 0,
        "B Line": 0,
        "C Line": -55,
        "D Line": 0,
        "E Line": 55,
        "F Line": 0,
        "H Line": 110,
    }

    fig, ax = plt.subplots(figsize=(7.2, 7.0), dpi=200)
    _setup_ax(ax)

    all_lon, all_lat = [], []
    for name in order:
        if name not in nets:
            continue
        lon, lat = nets[name]["lon"], nets[name]["lat"]
        off = offsets_m.get(name, 0)
        if off:
            lon, lat = _offset_polyline(lon, lat, off)
        _draw_polyline(ax, lon, lat, RR_COLORS[name], lw=LW - 0.4, z=2)
        stops = nets[name]["stops"]
        # subsample markers a bit for dense RapidRide stops
        idx = np.linspace(0, len(stops) - 1, min(len(stops), 18)).astype(int)
        _stations(ax, stops.stop_lon.iloc[idx], stops.stop_lat.iloc[idx], s=14, z=4)
        all_lon.append(lon)
        all_lat.append(lat)

    # Labels: unique terminals only
    placed = set()
    label_specs = [
        # (text, lon, lat, dx, dy, ha, va) — filled from stop endpoints
    ]
    # Labels use direction_id=0 trip order (see DIR_MAP in kingcounty_experiment.py):
    # A SB→Federal Way, B EB→Redmond, C SB→West Seattle, D/E NB→Ballard/Aurora, F EB→Renton.
    endpoint_labels = {
        "A Line": [("Tukwila Intl Blvd", "first"), ("Federal Way TC", "last")],
        "B Line": [("Bellevue TC", "first"), ("Redmond TC", "last")],
        "C Line": [("South Lake Union", "first"), ("West Seattle", "last")],
        "D Line": [("Ballard", "last")],  # downtown shared
        "E Line": [("Aurora Village", "last")],
        "F Line": [("Burien TC", "first"), ("Renton", "last")],
        "H Line": [],  # Burien + downtown already covered
    }
    # Manual placement tweaks (degrees)
    tweaks = {
        "Federal Way TC": (0.01, -0.01, "left", "top"),
        "Tukwila Intl Blvd": (0.022, -0.028, "left", "top"),
        "Bellevue TC": (0.01, -0.008, "left", "top"),
        "Redmond TC": (0.01, 0.006, "left", "bottom"),
        "West Seattle": (-0.015, -0.01, "right", "top"),
        "South Lake Union": (0.008, 0.01, "left", "bottom"),
        "Ballard": (-0.02, 0.006, "right", "bottom"),
        "Aurora Village": (-0.01, 0.008, "right", "bottom"),
        "Burien TC": (-0.02, -0.008, "right", "top"),
        "Renton": (0.01, -0.006, "left", "top"),
        "Downtown Seattle": (-0.045, 0.0, "right", "center"),
    }

    for name, specs in endpoint_labels.items():
        if name not in nets:
            continue
        stops = nets[name]["stops"]
        for text, which in specs:
            if text in placed:
                continue
            row = stops.iloc[0] if which == "first" else stops.iloc[-1]
            dx, dy, ha, va = tweaks.get(text, (0.008, 0.006, "left", "bottom"))
            _label(ax, row.stop_lon, row.stop_lat, text, dx=dx, dy=dy, ha=ha, va=va, size=8.5)
            placed.add(text)

    # Downtown Seattle label near the C/D/E/H bundle
    # Use a downtown stop on D Line (direction 0 ends downtown)
    if "D Line" in nets:
        d = nets["D Line"]["stops"]
        # pick stop closest to downtown core
        core_lon, core_lat = -122.3321, 47.6062
        d2 = (d.stop_lon - core_lon) ** 2 + (d.stop_lat - core_lat) ** 2
        i = int(d2.idxmin()) if hasattr(d2, "idxmin") else int(np.argmin(d2.to_numpy()))
        # idxmin on Series returns index label
        if isinstance(i, (int, np.integer)) and i in d.index:
            row = d.loc[i]
        else:
            row = d.iloc[int(np.argmin(d2.to_numpy()))]
        if "Downtown Seattle" not in placed:
            dx, dy, ha, va = tweaks["Downtown Seattle"]
            _label(ax, row.stop_lon, row.stop_lat, "Downtown Seattle", dx=dx, dy=dy, ha=ha, va=va, size=8.5)

    _legend(ax, [(n, RR_COLORS[n]) for n in order if n in nets], loc="lower left")

    all_lon = np.concatenate(all_lon)
    all_lat = np.concatenate(all_lat)
    pad_x, pad_y = 0.04, 0.03
    ax.set_xlim(all_lon.min() - pad_x, all_lon.max() + pad_x)
    ax.set_ylim(all_lat.min() - pad_y, all_lat.max() + pad_y)

    fig.tight_layout(pad=0.2)
    out = FIG / "fig_kingcounty_network.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(FIG / "fig_kingcounty_network.png", bbox_inches="tight", pad_inches=0.08, dpi=200)
    plt.close(fig)
    print("wrote", out)
    return out


if __name__ == "__main__":
    plot_phoenix()
    plot_king_county()
