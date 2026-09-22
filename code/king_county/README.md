# King County RapidRide experiment

Line-level AM boardings → stop OD on GTFS sequences → cross-line + monthly Newell.

```
python code/king_county/kingcounty_experiment.py
```

## Inputs
- `data/King_county/average_weekday_boardings_rapidride.csv` (AM 5–9am, directed route, month)
- `data/King_county/GTFS/` (stop sequences and coordinates)

## Outputs (`code/king_county/output/`)
- `line_od_diagnostics.csv`
- `od_A_NB_202310.csv` (example)
- `cross_line_newell_refmonth.csv`
- `monthly_system_boardings.csv`
- `experiment_summary.json`
- `fig_kingcounty_monthly.pdf` (also in `figures/`)

## Main numbers (current run)
- 14 directed RapidRide sequences; 750 route–month OD estimates
- Line boardings recovered to machine precision; mean trip ≈ 3.5 km
- Cross-line Newell (Oct 2023): **6.4%** vs uniform, **3.5%** vs archived frequencies (83 trips/h across all 14 directed routes)
- Monthly Newell (Apr 2020–May 2024): **2.1%**

Note: `Boardings counts` values with thousands separators (e.g. `"1,459"`) are stripped before `pd.to_numeric`, so counts ≥ 1,000 are retained.
