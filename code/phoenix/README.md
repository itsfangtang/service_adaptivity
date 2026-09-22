# Phoenix monthly experiment

Origin-only monthly boardings → production-constrained gravity OD → monthly Newell check.

```
# from repo package root
python code/phoenix/phoenix_monthly_experiment.py
```

(Uses the machine’s `pandas`/`numpy`/`matplotlib` environment.)

## Inputs
- `data/Phoenix/boardings-by-station-database---fy09-to-present-1738184335.xlsx`
- `data/Phoenix/GTFS/stops.txt` (coordinates)
- `data/Phoenix/GMNS/` (network context; distances use great-circle on stop coords)

## Outputs (`code/phoenix/output/`)
- `station_coordinate_match.csv`
- `monthly_od_diagnostics.csv`
- `od_YYYYMM.csv` (example month)
- `monthly_newell_shares.csv`
- `experiment_summary.json`
- `fig_phoenix_monthly.pdf` (also copied to `figures/`)

## Main numbers (current run)
- 46/46 light-rail stations matched
- β ≈ 0.115 /km; mean trip ≈ 7.2 km (Oct 2023 calibration)
- Apr 2020–Jun 2024 Newell saving vs uniform: **1.37%**
- Calendar 2019: **0.11%**
