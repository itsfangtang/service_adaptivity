"""Check how the BART files in data/BART connect (no DTALite run).

1. demand.csv.gz -> GMNS/OD_demand_td.csv: date filter 2024-10-01..2025-04-01, row-for-row identical.
2. GTFS feed and calendar: which service pattern the GMNS network encodes.
3. GMNS node/link counts (50 stations, 380 service nodes, 362 service links, 1,122 links).
4. route_assignment.csv: which demand hour DTALite assigned, path counts, prob shares.
5. A station-direction boarding stream built from route_assignment (Eq. od-map) for one example.

Run from the repository root (reads the 40.6 M-row archive; about 1-2 minutes):
    python -I code/bart/bart_data_lineage.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
B = ROOT / "data" / "BART"
OUT = Path(__file__).resolve().parent / "output"
KEY = ["date", "hour", "origin", "destination"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rep: dict = {}

    # 1. archive -> analysis window
    raw = pd.read_csv(B / "demand.csv.gz")
    rep["archive_rows"] = len(raw)
    rep["archive_dates"] = int(raw.date.nunique())
    rep["archive_range"] = [raw.date.min(), raw.date.max()]
    rep["archive_hours"] = sorted(int(h) for h in raw.hour.unique())
    sub = raw[(raw.date >= "2024-10-01") & (raw.date <= "2025-04-01")]
    td = pd.read_csv(B / "GMNS" / "OD_demand_td.csv")
    m = sub.merge(td, on=KEY, how="outer", indicator=True, suffixes=("", "_td"))
    rep["od_td_rows"] = len(td)
    rep["od_td_identical_to_archive_window"] = bool((m._merge == "both").all() and (m.volume == m.volume_td).all())
    rep["od_td_same_station_rows"] = int((td.origin == td.destination).sum())

    # 2. GTFS
    feed = pd.read_csv(B / "GTFS" / "feed_info.txt")
    cal = pd.read_csv(B / "GTFS" / "calendar.txt")
    rep["gtfs_feed"] = feed.iloc[0].astype(str).to_dict()
    rep["gtfs_service_ids"] = cal.service_id.tolist()
    rep["gtfs_calendar_range"] = [int(cal.start_date.min()), int(cal.end_date.max())]

    # 3. GMNS network
    node = pd.read_csv(B / "GMNS" / "node.csv")
    link = pd.read_csv(B / "GMNS" / "link.csv")
    rep["nodes"] = node.node_type.value_counts().to_dict()
    rep["links"] = link.link_type_name.value_counts().to_dict()
    rep["links_total"] = len(link)
    rep["directed_routes"] = int(link.directed_route_id.nunique())

    # 4. route_assignment: identify the assigned hour
    ra = pd.read_csv(B / "GMNS" / "route_assignment.csv")
    seed = ra.groupby(["o_zone_id", "d_zone_id"]).seed_od_volume.first()
    h7 = raw[raw.hour == 7]
    match = []
    for d, g in h7.groupby("date"):
        if g.volume.sum() != 14900:  # total read by DTALite (summary_log_file.txt)
            continue
        s = g.set_index(["o_zone_id", "d_zone_id"]).volume
        j = seed.to_frame().join(s, how="left").fillna(0)
        if (j.seed_od_volume == j.volume).all():
            match.append(d)
    rep["dtalite_demand_hour"] = {"dates_matching_hour7_seed": match,
                                  "summary_log_total": 14900,
                                  "assigned_total": float(seed.sum())}
    rep["route_assignment"] = {
        "paths": len(ra), "od_pairs": int(len(seed)),
        "paths_per_od": ra.groupby(["o_zone_id", "d_zone_id"]).size().value_counts().sort_index().to_dict(),
        "prob_sum_per_od_minmax": [float(ra.groupby(["o_zone_id", "d_zone_id"]).prob.sum().min()),
                                   float(ra.groupby(["o_zone_id", "d_zone_id"]).prob.sum().max())],
        "max_abs(volume - prob*seed)": float((ra.volume - ra.prob * ra.seed_od_volume).abs().max()),
        "inaccessible_od": int(len(pd.read_csv(B / "GMNS" / "inaccessible_od.csv"))),
    }

    # 5. boarding streams: first boarding link of each path, weighted by prob (Eq. od-map)
    ltype = link.set_index("link_id").link_type_name
    def boards(seq):
        return [int(x) for x in str(seq).split(";") if x and ltype.get(int(x)) == "boarding_links"]
    ra["boarding_links"] = ra.link_ids.map(boards)
    rep["route_assignment"]["boardings_per_path"] = ra.boarding_links.map(len).value_counts().to_dict()
    ra["board_link"] = ra.boarding_links.str[0]
    eta = ra[["o_zone_id", "d_zone_id", "board_link", "prob"]]
    bl = link.set_index("link_id")[["from_node_id", "directed_route_id", "route_short_name"]]
    eta = eta.join(bl, on="board_link")
    st = node.set_index("node_id").name
    eta["station"] = eta.from_node_id.map(st)
    eta.to_csv(OUT / "path_boarding_incidence.csv", index=False)
    # example: MacArthur by line-direction for the mean weekday 08:00 hour
    wk = td[(td.day_type == "Weekday") & (td.origin != td.destination) & (td.hour == 8)]
    y = wk.groupby(["o_zone_id", "d_zone_id"]).volume.sum() / wk.date.nunique()
    e = eta[eta.station == "MCAR"].join(y.rename("y"), on=["o_zone_id", "d_zone_id"]).fillna({"y": 0})
    e["lam"] = e.prob * e.y
    by_line = e.groupby("route_short_name").lam.sum().round(1)
    od_total = float(y[y.index.get_level_values(0) == int(node.loc[node.name == "MCAR", "node_id"].iloc[0])].sum())
    rep["example_MCAR_0800_mean_weekday"] = {
        "station_total_from_od": round(od_total, 1),
        "covered_by_route_assignment_paths": round(float(by_line.sum()), 1),
        "by_line_direction": by_line.to_dict(),
    }
    (OUT / "data_lineage.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=2, default=str))


if __name__ == "__main__":
    main()
