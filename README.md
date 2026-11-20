# The Value of Service Adaptivity — open data and code

Companion repository for

> Xuesong (Simon) Zhou and Fang (Alicia) Tang.
> *The Value of Service Adaptivity: Two-Timescale Frequency Planning with an Open San Francisco Bay Area Rail Dataset.*
> Urban Rail Transit (under review, 2026).

Archived release: **v1.0.0, DOI [10.5281/zenodo.24387602](https://doi.org/10.5281/zenodo.24387602)** (all versions: [10.5281/zenodo.24387601](https://doi.org/10.5281/zenodo.24387601)).

The repository holds three things:
- the open BART dataset: hourly station-to-station OD, GTFS, a GMNS network, and DTALite paths;
- the event loader and exact within-day dynamic program, with the nested day-to-day evaluation;
- the thinner-data checks for Phoenix and Seattle.

Every number in the paper that is computed (not assumed) can be regenerated from these files. **New users should start with [TEACHING_GUIDE.md](TEACHING_GUIDE.md)**. It explains how the OD demand, the link and path files, and the dynamic program fit together.

## Quick start

```bash
pip install numpy pandas matplotlib openpyxl
cd code
python make_demand.py && python reproduce_boards.py && python verify.py && python s6_nested.py
cd ..
python -I code/bart/bart_observed_demand.py
python -I code/bart/bart_macarthur.py
```

The scripts need Python 3.9 or later. The full list of scripts, with the paper exhibit each one reproduces and its expected output, is in [`code/README.md`](code/README.md) (model results) and [`code/bart/README.md`](code/bart/README.md) (observed BART results).

## What reproduces what

| Paper exhibit | Script | Data |
|---|---|---|
| Figs 5, 6, 8; Table 3 (08:00 keep/switch) | `code/reproduce_boards.py`, `code/contval.py` | modeled 30×24 demand |
| Fig 9 (exact-count curves, hull break-even charges) | `code/curves.py`, `code/fig_curves.py`, `code/dayDP.py` | modeled |
| Table 5 (partition, Newell 2,595.5), Table 6, App. A.3 | `code/s4_partition.py`, `code/s4_drift.py` | modeled |
| Fig 10 (shock shape) | `code/s5_shape.py` | modeled |
| Table 8 (value of M within-day stages and N daily plans) | `code/s6_nested.py` | modeled + 2.5% hourly noise, seed 19 |
| DP = complete enumeration (64,729 plans) | `code/verify.py` | modeled |
| Fig 11 (123 weekdays, mean 167,988, CV 0.149); 8.7% systemwide | `code/bart/bart_observed_demand.py`, `code/bart/bart_newell_systemwide.py` | `data/BART/GMNS/OD_demand_td.csv` |
| Fig 12 (MacArthur 81.8 vs 66.7 pax-h, 18.4%) | `code/bart/bart_macarthur.py` | same |
| Figs 3 and 6 input profiles (24th St Mission) | `code/bart/bart_24th_profiles.py` | `data/BART/demand.csv.gz` |
| Fig 7, Section 2.5 (network, paths, boarding resources) | `code/bart/bart_data_lineage.py` | `data/BART/GMNS/`, `data/BART/column_pool/` |
| Table 10, Appendix D (Phoenix 1.37%, Seattle 6.4%) | `code/phoenix/…`, `code/king_county/…` | `data/Phoenix/`, `data/King_county/` |

## Data

### BART (`data/BART/`)

| File | Content |
|---|---|
| `demand.csv.gz` | BART public hourly OD ridership: 1,924 dates, 1 Oct 2019–1 Apr 2025, hours 05–23, 50 stations. Fields: `date, hour, day_type, origin, o_zone_id, destination, d_zone_id, volume`. |
| `GMNS/OD_demand_td.csv` | The paper's analysis window: the rows of `demand.csv.gz` dated 1 Oct 2024–1 Apr 2025, which is 174 dates (123 weekdays). Same fields. |
| `GTFS/` | BART feed version 68, valid 1–14 Jan 2024. It carries the weekday service pattern introduced on 11 Sep 2023. |
| `GMNS/node.csv`, `GMNS/link.csv` | The GTFS 07:00–08:00 trips converted to GMNS: 50 stations and 380 service nodes (430 nodes); 380 boarding, 380 alighting and 362 service links (1,122 links). |
| `GMNS/OD_demand_7_Wed.csv` | The DTALite input: the 07:00 hour of Wed 12 Feb 2025 (1,668 OD cells, 14,900 trips). |
| `GMNS/route_assignment.csv` | DTALite path assignment for that hour: 2,971 paths over 1,341 OD pairs, with path shares `prob`. |
| `column_pool/columns.csv` | The full candidate path set used in the paper: 4,898 paths over all 2,450 OD markets, as link sequences. |
| `GMNS/run_dtalite.py` | Rebuilds the assignment. It needs the `DTALite` Python package and overwrites `node.csv` and `link.csv` in place, so run it on a copy. |

Holidays are absent from the archive rather than flagged. The paper drops same-station records (origin = destination) in all of its statistics.

### Phoenix (`data/Phoenix/`) and Seattle (`data/King_county/`)

- **Phoenix:** Valley Metro Rail monthly boardings by station (FY2009 onward). The archive covers the single-line system that ran before June 2025, with 46 station records.
- **Seattle:** King County Metro RapidRide average weekday AM boardings by directed route and month, through May 2024 (lines A–F and H; the G Line opened in September 2024).

Both folders include GTFS and GMNS files. Their OD matrices are gravity estimates, not surveyed travel; see the teaching guide, Section 9.

## Notes on the code

- **Departure timing.** `code/evloader.py` implements the paper's rule that after a change of action the next departure comes max{0, 60/f_new − φ} minutes later.
  - Release v1.0.0 scheduled it too early when a change fell between departures, which never happens on the whole-hour grid the paper uses.
  - This was fixed after v1.0.0, and `code/tests/test_evloader_phase.py` covers it. Every published number is unchanged.
- **End-of-day clearance.** Passengers still waiting at 24:00 are cleared at no operating charge. In the Table 8 solutions the residual queue is zero to numerical tolerance.

## Citation

```bibtex
@article{zhou2026adaptivity,
  title   = {The Value of Service Adaptivity: Two-Timescale Frequency Planning
             with an Open San Francisco Bay Area Rail Dataset},
  author  = {Zhou, Xuesong and Tang, Fang},
  journal = {Urban Rail Transit},
  note    = {Under review},
  year    = {2026}
}
@software{tang2026serviceadaptivity,
  author  = {Tang, Fang and Zhou, Xuesong},
  title   = {service\_adaptivity: open data and code},
  version = {1.0.0},
  doi     = {10.5281/zenodo.24387602},
  year    = {2026}
}
```

## Acknowledgments and license

This work was supported by the U.S. National Science Foundation CMMI LEAP-HI program, Award No. 2053373.

- The code in `code/` is under the MIT license (see `LICENSE`).
- The agency data in `data/` (BART; Valley Metro / City of Phoenix; King County Metro) keep their publishers' terms. Please cite the agencies when you reuse them.
