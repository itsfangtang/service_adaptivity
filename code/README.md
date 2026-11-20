# Compact package: event loader, exact within-day DP and nested evaluation

Reproduces the modeled results of Sections 2-6 and Appendix A.3 of the paper, and the
Section 8 / Appendix D checks on Phoenix and King County. Exhibit numbers below follow the
current manuscript. Demand for Sections 2-4 is the archived **modeled** 30x24 recovery
matrix `demo_sensor_demand_30x24.csv` (rows = days 1-30, columns = hours 0-23, passengers/h);
it is not observed BART counts. Day *d* of the paper is row `d-1` (day 10 = `D[9]`).

Requirements: Python 3.9+ with `numpy`; `matplotlib` for figures; `pandas` and `openpyxl`
for the Section 8 scripts. Run the scripts in this folder from `code/` (they read and write
relative paths); run the Section 8 scripts from the repository root.

## Scripts, exhibits and expected numbers

| Script (run from `code/`) | Paper exhibit | Expected output |
|---|---|---|
| `python make_demand.py` | input | CSV -> `demand.npy` |
| `python reproduce_boards.py` | Fig. 5, Fig. 6, Fig. 8, Table 3 | queue after 08:00 departure 419.8; 09:00 queue/waiting keep (4,6) 906.5 / 831.9, switch (6,6) 231.5 / 494.4; queue at 10:00 about 988; day 1 08-09 waiting 137.4 (f=4) and 91.6 (f=6) pax-h |
| `python verify.py` | Section 3.4 (computation) | DP = complete enumeration of the 64,729 plans with at most 3 stages, for c_E = 1 and 0 (about 1-2 min) |
| `python dayDP.py 9` | Fig. 9, day 10 | J(m), m = 1..5: 23,317.7 / 20,149.4 / 16,612.6 / 14,373.6 / 11,887.5 (c_E = 1); 3,714.8 ... 3,585.1 (c_E = 0) |
| `python contval.py` | Table 3 (08:00 keep/switch) | keep: 879.9, 13,433.4, 19,070.2, (4,8) from 15:00; switch: 566.4, 16,569.4, 21,892.6; with M<=4 keep gives 14,373.6 = J(4); with c_E = 0 the switch wins |
| `python curves.py` | Fig. 9 data -> `curves.json` | J(m), m <= 8, days 1, 10, 20, 30; day-10 gains 3,168.3 and 3,536.8; hull break-even charges 3,352.6, 2,362.6, 474.1; five stages save 49% (c_E = 1) and 3.5% (c_E = 0); at most 170 labels per interval |
| `python fig_curves.py` | Fig. 9 panels (a), (b) | `fig_Jstar_M.pdf/png` (panel (c), the net-cost curves, is not drawn by this script) |
| `python s4_partition.py` | Table 5 | Newell optimum 2,595.5 pax-h; L(m) = 289.5, 159.0, 57.9, 46.9, 35.1, 24.7, 16.0, 12.9 |
| `python s4_drift.py` | Table 6, Appendix A.3 | a = T = 1, m = 4, 8, 16: unused 1/(2m) at max placement; falling demand at mean placement waiting 1/(12 m^2) = 0.005208, 0.001302, 0.000326 |
| `python s5_shape.py` | Fig. 10 | uniform factor 0.40 gives sqrt(0.40) = 0.632 at every m; period factors 0.62 (m = 1), 0.58 (m = 2), 0.43-0.46 (m >= 3); `s5_shape.json`, `fig_shape_shock.pdf/png` |
| `python s6_nested.py` | Table 8 | all cells of Table 8 (rows M = 1, 3, 5; M = 2, 4 also printed); `s6_nested.json` (about 15-30 s) |
| `python tests/test_evloader_phase.py` | loader rule, Section 3.4 | departure phase after a change; prints `all tests passed` |

| Script (run from repository root) | Paper exhibit | Expected output |
|---|---|---|
| `python code/phoenix/phoenix_monthly_experiment.py` | Section 8, Table 10; Appendix D, Table D2, Fig. D1 | 46/46 stations; beta = 0.115 /km, mean trip 7.2 km; Apr 2020-Jun 2024 (45 months) 1.37%; calendar 2019 0.11% |
| `python code/king_county/kingcounty_experiment.py` | Section 8, Table 10 | 14 directed routes, 750 route-month records, mean trip 3.5 km; Oct 2023 (83 trips/h) 6.4% vs uniform, 3.5% vs archived frequencies (archived 3.0% below uniform); Apr 2020-May 2024 (50 months) 2.1% |

The two Section 8 scripts write to `code/<system>/output/` and also copy their figure to
`figures/` at the repository root.

## Conventions (paper Sections 2-3)

- FIFO boarding; arrivals at the instant of a departure board it. Capacity per departure is
  kappa*n with kappa = 56.25 spaces/car (337.5 for 6 cars, 450 for 8 cars).
- Actions (f, n) in {(2,8), (3,6), (3,8), (4,6), (4,8), (6,6), (6,8)}; transitions only at
  whole hours. The day starts empty with phase 0 (first departure at 0 + headway).
- Departure timing (`evloader.simulate_segment`): departures continue from the last
  departure with the headway of the action in force. When the action changes at t0, the
  next departure is at max(t0, last departure + 1/f_new), i.e. max{0, 60/f_new - phi}
  minutes after the change. A departure exactly at a boundary runs under the action of
  the interval it closes. With whole-hour transitions and f in {2,3,4,6} every headway
  divides the hour, so phi = 0 at every transition in the reported runs.
- Weights: c0 = cQ = 1 per pax-h, cE = 1 (base) or 0 per unused space, operating cost 2
  per car-departure, zero transition charges unless stated.
- End of day: passengers still waiting after the last departure at or before 24:00 are
  cleared free (no operating charge, no terminal term); their waiting up to 24:00 is
  charged. No passengers remained in any reported day.
- Label dominance at a node (h, i, u-, phi): q1 <= q2 and C1 + cE (q2 - q1) <= C2.

## Table 8 setup (`s6_nested.py`)

- Demand: lambda_d(h) = (1 - delta r(d)) * full(h) * (1 + eps_{d,h}), r(d) = exp(-(d-1)/10.5),
  30 days, `full` the modeled full-recovery weekday profile in the script, eps_{d,h} i.i.d.
  N(0, 0.025^2) (2.5% hourly Gaussian noise) from `numpy.random.default_rng(19)`. The
  generator is re-seeded for each delta in {0.30, 0.58, 0.80}, so all depths use the same draws.
- Candidate pool: the union, duplicates removed, of the exact day-optimal plans with exactly
  m = 1, ..., 5 stages on every day (from `dayDP.day_dp`). Allowance M keeps the pool plans
  with at most M stages. Each pool plan is evaluated on every day with the event loader.
- Across days: exact partition of the 30 days into at most N blocks, one pool plan per
  block, zero plan-change charges; entries are % saving against the best single one-stage
  plan for the whole recovery (M = N = 1). Values are hindsight (known demand).
