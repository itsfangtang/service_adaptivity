# BART observed-data reproduction (Section 7 of the paper)

These scripts reproduce every BART number the paper computes from observed data:
Figure 11 and its statistics, the systemwide 8.7% Newell benchmark, the MacArthur
check (Figure 12, 18.4%), and the observed 24th St Mission profiles drawn in
Figures 3 and 6. They also document how the files under `data/BART/` connect.
They need only `numpy`, `pandas` and `matplotlib`; DTALite is not run.

Run every command from the repository root. Outputs go to `code/bart/output/`.

| Script | Inputs | Main outputs |
|---|---|---|
| `bart_observed_demand.py` | `data/BART/GMNS/OD_demand_td.csv` | `observed_demand_stats.json`, `weekday_day_hour_demand.csv` (123 x 19), `fig11_profile.csv`, `fig11_daily_totals.csv`, `fig11_observed_demand.png` |
| `bart_newell_systemwide.py` | `output/weekday_day_hour_demand.csv` (or the OD file) | `newell_systemwide.json` |
| `bart_macarthur.py` | `data/BART/GMNS/OD_demand_td.csv` | `macarthur_MCAR.json`, `fig12_macarthur_MCAR.png` |
| `bart_24th_profiles.py` | `data/BART/demand.csv.gz` | `fig03_fig06_24th_profiles.csv` |
| `bart_data_lineage.py` | `data/BART/demand.csv.gz`, `GMNS/*`, `GTFS/*` | `data_lineage.json`, `path_boarding_incidence.csv` |

```bash
python -I code/bart/bart_observed_demand.py      # ~20 s
python -I code/bart/bart_newell_systemwide.py
python -I code/bart/bart_macarthur.py            # add --use-paper-rates to use the rounded rates
python -I code/bart/bart_24th_profiles.py        # reads the 40.6 M-row archive, ~1 min
python -I code/bart/bart_data_lineage.py         # reads the archive, ~1-2 min
```

## Conventions

- Analysis window: 1 October 2024 to 1 April 2025, which gives 174 dates. `OD_demand_td.csv` is exactly this date slice of `demand.csv.gz`, row for row.
- Weekday: `day_type == "Weekday"`, which coincides with Monday to Friday. This gives 123 dates. Holidays are not removed by a rule: the archive simply has no records for 11 Nov, 28–29 Nov and 25 Dec 2024, or for 1 Jan, 20 Jan and 17 Feb 2025. Saturday 15 Feb and Monday 31 Mar 2025 are also missing.
- Same-station records (origin = destination) are excluded, except in the 24th St profiles (see below).
- Hours: 05 to 23, which are the only hours in the archive. The bins are one hour long.

## Expected output

| Quantity | Paper | Script value |
|---|---|---|
| Dates / weekdays | 174 / 123 | 174 / 123 |
| Mean weekday boardings | 167,988 | 167,988.3 |
| CV of daily totals | 0.149 | 0.1494 (ddof=1), 0.1487 (ddof=0) |
| Mean profile, 05:00 / 08:00 / 17:00 | 2,176 / 18,246 / 19,728 | 2,176 / 18,246 / 19,728 |
| Systemwide square-root saving, 19 h | 8.7% | 8.65% |
| MacArthur 05–08 rates (pax/h) | 33.9, 115.9, 306.2, 525.7 | 33.9, 115.9, 306.2, 525.7 |
| MacArthur uniform, event-based | 81.8 pax-h, 5.0 min | 81.80 pax-h, 5.00 min |
| MacArthur square root, event-based | 66.7 pax-h, 18.4% | 66.73 pax-h, 18.42% |
| MacArthur 1-minute-grid optimum | 66.2 | 66.23 |
| MacArthur continuum saving | 17.2% | 17.22% |
| Fig. 6 peak, 24th St, mean Mon–Thu 7–10 Oct 2019 | 2,362 | 2,362.2 (with same-station records; 2,357.5 without) |

Notes:
- The systemwide saving is `1 - (sum sqrt(lambda))^2 / (H * sum lambda)` with H = 19. It does not depend on the departure total.
- The MacArthur rates are station totals: all lines and directions boarding at `MCAR`. `bart_data_lineage.py` splits the 08:00 rate (525.7) by the DTALite boarding links: Yellow-S 317.1, Red-S 72.3, Orange-S 60.2, Orange-N 40.5, Yellow-N 23.8. These sum to 513.9; the remainder is OD pairs that have no path in `route_assignment.csv`.
- The archive starts at 05:00, so the 00:00–04:00 segment drawn in Figure 3(a) is not in this repository.

## Provenance

The logic for the Figure 11 statistics and the 8.7% saving is ported from the author's
`build_multiclock_demand_figure.py`, found in the v1.9 student package at
`release_packages/version_8/paper/tools/`. The MacArthur calculation is ported from an
independent check script, `macarthur.py`, written during the paper's mathematics review.
Each script names its source in its docstring.
