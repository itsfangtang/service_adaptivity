# Adaptive Public Transit Service Planning

**Companion data and code** for:

> Xuesong (Simon) Zhou and Fang (Alicia) Tang.  
> *Adaptive Public Transit Service Planning: A Multi-Timescale Decision Framework*  
> (manuscript, September 2026)

This repository packages the compact computational archive used in the paper: the event-based loader and exact within-day dynamic program on a modeled recovery demand matrix, the archived BART hourly OD inputs for the main application, and the Phoenix and King County experiments under thinner public ridership inputs (Section 8 of the paper).

## Overview

Transit agencies must decide how often, when, and by how much to revise a committed service plan when demand changes and information is incomplete. The paper scores candidate plans with an event-based account of arrivals and boardings (ordinary waiting, left-behind waiting, and unused capacity), solves the within-day problem by a label-setting dynamic program on a finite grid of transition times, and nests that day problem across a recovery.

**What this package reproduces**

| Component | Role in the paper |
|---|---|
| Modeled 30×24 recovery demand + exact DP | Main Boards / Figures for within-day and nested day-to-day results |
| BART hourly station-to-station OD | Main application: recovery demand construction and service adaptivity |
| Valley Metro Rail (Phoenix) monthly boardings | Section 8: origin-only monthly Newell check |
| King County Metro RapidRide AM boardings | Section 8: line-level Newell checks |

**What is not in this package**

- The illustrative full-day Red Line stress-replay values reported from an earlier archived experiment (see the paper’s data-availability statement).

## Repository layout

```
.
├── README.md                 # this file
├── data/
│   ├── BART/                 # BART hourly ridership + GTFS + GMNS
│   ├── Phoenix/              # Valley Metro boardings + GTFS + GMNS
│   └── King_county/          # RapidRide AM boardings + GTFS + GMNS
└── code/
    ├── README.md             # DP / Section 3–6 reproduction notes
    ├── demo_sensor_demand_30x24.csv
    ├── evloader.py, dayDP.py, …   # exact within-day and nested scripts
    ├── phoenix/              # Phoenix monthly experiment
    └── king_county/          # King County RapidRide experiment
```

## Requirements

- Python 3.9+ recommended
- `numpy`, `pandas`
- `matplotlib` (figures)
- `openpyxl` (Phoenix `.xlsx` boardings workbook)

Install with:

```bash
pip install numpy pandas matplotlib openpyxl
```

Run scripts from the repository root (or follow the paths noted in each subdirectory README).

## Reproducing the main modeled results

The compact DP package uses an archived **modeled** 30×24 recovery demand matrix (`code/demo_sensor_demand_30x24.csv`), not observed BART counts. Conventions match the paper (FIFO; whole-hour transitions; weights \(c_0=c_Q=1\), \(c_E\in\{0,1\}\), 2 per car-departure; \(\kappa=56.25\) spaces/car).

```bash
cd code
python make_demand.py          # CSV -> demand.npy
python reproduce_boards.py     # loader checks against Board numbers
python verify.py               # exact DP == full enumeration (M<=3)
python dayDP.py 9              # J*(M) for day 10, M<=5
python contval.py              # keep/switch continuation values
python curves.py               # exact-count curves -> curves.json
python fig_curves.py           # Figure 7
python s4_partition.py         # partition / excess-waiting table
python s4_drift.py             # Appendix drift checks
python s5_shape.py             # shape vs uniform shock
python s6_nested.py            # nested M–N evaluation
```

Details and expected numerical conventions are in [`code/README.md`](code/README.md).

## Reproducing the Section 8 experiments

### Phoenix (origin-only monthly boardings)

```bash
python code/phoenix/phoenix_monthly_experiment.py
```

**Inputs:** `data/Phoenix/boardings-by-station-database---fy09-to-present-1738184335.xlsx`, `data/Phoenix/GTFS/`, `data/Phoenix/GMNS/`  
**Outputs:** `code/phoenix/output/` (OD diagnostics, monthly Newell shares, `experiment_summary.json`) and `figures/fig_phoenix_monthly.pdf`

### King County RapidRide (line-level AM boardings)

```bash
python code/king_county/kingcounty_experiment.py
```

**Inputs:** `data/King_county/average_weekday_boardings_rapidride.csv`, `data/King_county/GTFS/`  
**Outputs:** `code/king_county/output/` and `figures/fig_kingcounty_monthly.pdf`

**Headline numbers (current run):** 14 directed routes; 750 route–month OD estimates; October 2023 has 83 trips/h; square-root vs uniform **6.4%**; vs archived frequencies **3.5%**; monthly AM total (50 months) **2.1%**.

See [`code/king_county/README.md`](code/king_county/README.md).

## Data description and provenance

### BART (`data/BART/`)

| File / folder | Content |
|---|---|
| `demand.csv.gz` | Archived hourly station-to-station OD volumes (gzipped CSV) |
| `GTFS/` | BART public schedule snapshot |
| `GMNS/` | Network nodes and links derived for impedance / context |

`demand.csv.gz` fields: `date`, `hour`, `day_type` (Weekday / Saturday / Sunday), `origin`, `o_zone_id`, `destination`, `d_zone_id`, `volume`. Coverage is roughly October 2019–April 2025, operating hours 5–23, across 50 BART stations. This is the archived hourly OD table used in the main application; schedules and published ridership remain public from BART.

### Phoenix / Valley Metro Rail (`data/Phoenix/`)

| File / folder | Content |
|---|---|
| `boardings-by-station-database---fy09-to-present-1738184335.xlsx` | Monthly boardings by station (agency open data) |
| `GTFS/` | Public transit schedule snapshot (City of Phoenix / Valley Metro feed) |
| `GMNS/` | Network nodes and links derived for impedance / context |

Estimated monthly OD matrices are **production-constrained gravity** outputs under a calibrated distance decay; they are not surveyed Phoenix travel.

### King County Metro RapidRide (`data/King_county/`)

| File / folder | Content |
|---|---|
| `average_weekday_boardings_rapidride.csv` | Average weekday AM (5–9am) boardings by directed RapidRide route and month |
| `GTFS/` | King County Metro (and related) GTFS snapshot for stop sequences |
| `GMNS/` | Network nodes and links |

Stop-level OD on each line is estimated from line totals and the GTFS sequence under a declared mid-route prior and forward gravity rule; not surveyed OD. Boarding counts with thousands separators are stripped before numeric conversion so routes with ≥1,000 riders are retained.

### Third-party data terms

Agency ridership files and GTFS feeds remain subject to the terms of their publishers (BART; Valley Metro / City of Phoenix; King County Metro). Redistribution in this archive is for research reproducibility accompanying the manuscript. Please cite the original agencies when reusing their data, and check current open-data licenses before commercial use.

## Citation

If you use this code or data, please cite the paper:

```bibtex
@unpublished{zhou2026adaptivity,
  title   = {Adaptive Public Transit Service Planning:
             A Multi-Timescale Decision Framework},
  author  = {Zhou, Xuesong and Tang, Fang},
  note    = {Manuscript},
  year    = {2026}
}
```

Update the BibTeX entry with the journal / DOI once the article is accepted.

## Acknowledgments

Supported by the U.S. National Science Foundation CMMI LEAP-HI program under Award No. 2053373, “Re-Engineering for Adaptable Lives and Businesses.”

## Contact

- Xuesong (Simon) Zhou  
- Fang (Alicia) Tang  

For questions about reproducing the main BART application numbers, contact the authors.

## License

- **Code** in `code/`: MIT (see `LICENSE`).
- **Agency data** in `data/`: retain original publisher rights and attribution; not relicensed by the authors.
