# Data-Informed Transit Service Adaptivity

**Companion data and code** for:

> Xuesong (Simon) Zhou and Fang (Alicia) Tang.  
> *Data-Informed Transit Service Adaptivity: A Nested Dynamic Programming Approach*  
> (manuscript, September 2026)

This repository packages the compact computational archive used in the paper: the event-based loader and exact within-day dynamic program on a modeled recovery demand matrix, the archived BART hourly OD inputs for the main application, and the Phoenix and King County appendix experiments under thinner public ridership inputs.

## Overview

Transit agencies must decide how often, when, and by how much to revise a committed service plan when demand changes and information is incomplete. The paper scores candidate plans with an event-based account of arrivals and boardings (ordinary waiting, left-behind waiting, and unused capacity), solves the within-day problem by a label-setting dynamic program on a finite grid of transition times, and nests that day problem across a recovery.

**What this package reproduces**

| Component | Role in the paper |
|---|---|
| Modeled 30×24 recovery demand + exact DP | Main Boards / Figures for within-day and nested day-to-day results |
| BART hourly station-to-station OD | Main application: recovery demand construction and service adaptivity |
| Valley Metro Rail (Phoenix) monthly boardings | Appendix: origin-only monthly Newell check |
| King County Metro RapidRide AM boardings | Appendix: line-level Newell checks |

**What is not in this package**

- The illustrative full-day Red Line stress-replay values reported from an earlier archived experiment (see the paper’s data-availability statement).

## Repository layout

```
.
├── README.md                 # this file
├── data/
    ├── BART/                 # BART hourly ridership + GTFS + GMNS
    ├── Phoenix/              # Valley Metro boardings + GTFS + GMNS
    └── King_county/          # RapidRide AM boardings + GTFS + GMNS
```

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

Stop-level OD on each line is estimated from line totals and the GTFS sequence under a declared mid-route prior and forward gravity rule; not surveyed OD.

### Third-party data terms

Agency ridership files and GTFS feeds remain subject to the terms of their publishers (BART; Valley Metro / City of Phoenix; King County Metro). Redistribution in this archive is for research reproducibility accompanying the manuscript. Please cite the original agencies when reusing their data, and check current open-data licenses before commercial use.

## Citation

If you use this code or data, please cite the paper:

```bibtex
@unpublished{zhou2026adaptivity,
  title   = {Data-Informed Transit Service Adaptivity:
             A Nested Dynamic Programming Approach},
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

- **Agency data** in `data/`: retain original publisher rights and attribution; not relicensed by the authors.
