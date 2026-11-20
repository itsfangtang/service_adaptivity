# Teaching guide: from open BART data to the value of service adaptivity

This guide is for a graduate student who wants to rebuild the paper's results and understand every step. It follows the data from the raw OD file to the dynamic program.

The guide is organized as follows:
- Sections 1–5 build the inputs.
- Sections 6–8 are the model.
- Section 9 covers the thinner-data cases.
- Section 10 has exercises.

Section numbers in brackets, such as [§2.5], refer to the paper.

```
demand.csv.gz ──filter dates──► OD_demand_td.csv ──hour, weekday mean──► y_{w,h}
GTFS ──07–08 trips──► GMNS node/link ──DTALite──► paths k, shares ω_{k|w}
                                     └─► column_pool/columns.csv (4,898 paths)
y_{w,h} × ω_{k|w} × boarding incidence η_{sk} ──► arrival rate λ_{s,h} at boarding resource s
λ_{s,h} ──► event loader (waiting, left behind, unused) ──► within-day DP ──► day-to-day nesting
```

## 1. Set up

```bash
pip install numpy pandas matplotlib openpyxl
git clone https://github.com/itsfangtang/service_adaptivity && cd service_adaptivity
```

Run the scripts in `code/bart/` from the repository root. Run the model scripts in `code/` from inside `code/`. Every script prints its key numbers, and the expected values are listed in `code/README.md` and `code/bart/README.md`.

## 2. OD demand: where `y_{w,h}` comes from

**The raw archive.** `data/BART/demand.csv.gz` is BART's public hourly ridership: 40.6 million rows over 1,924 dates, from 1 Oct 2019 to 1 Apr 2025.

Each row reads: on `date`, during entry `hour` (05–23), `volume` passengers entered at `origin` and exited at `destination`.
- `o_zone_id` and `d_zone_id` (1–50) are the station numbers that the GMNS network uses as zones.
- `day_type` is BART's Weekday / Saturday / Sunday label.

**The analysis window.** `data/BART/GMNS/OD_demand_td.csv` is the same table restricted to 1 Oct 2024–1 Apr 2025. That window has 174 dates: 123 weekdays, 25 Saturdays and 26 Sundays. To get the paper's weekday OD demand:
1. Keep the rows with `day_type == "Weekday"` (123 dates). Federal holidays are already missing from the archive.
2. Drop same-station records (origin = destination). These are entries and exits at one station, not trips.
3. Average over the 123 days for each (origin, destination, hour). This gives y_{w,h} for OD market w and hour h. There are 50 × 49 = 2,450 markets.

`code/bart/bart_observed_demand.py` performs these steps. It reproduces the mean weekday total of 167,988 boardings, a coefficient of variation of 0.149 across days, and Figure 11.

> **Check yourself.** Why is the mean profile not enough to plan service? Look at the 10th–90th percentile band in Figure 11(a) and the daily totals in panel (b).

## 3. Network: GTFS → GMNS node and link files

**The schedule.** `data/BART/GTFS/` is BART feed version 68. The feed is valid 1–14 Jan 2024, but its service IDs (`2023_09_11-…`) show that it carries the weekday pattern introduced on 11 September 2023; that is the pattern the paper uses. Only the trips between 07:00 and 08:00 were converted (124 trips), so the network is an AM-peak-hour snapshot.

**The GMNS conversion** (`data/BART/GMNS/node.csv`, `link.csv`):

| Object | Count | Meaning |
|---|---|---|
| `metro_station` node | 50 | one per physical station; `zone_id` = station number |
| `metro_service_node` | 380 | one per station × directed route × stop pattern (name such as `1.1.MCAR:…` = route 1.1, Yellow-S, at MacArthur) |
| `boarding_links` | 380 | station → service node; this is the **boarding resource** s of the paper |
| `deboarding_links` | 380 | service node → station |
| `service_links` | 362 | service node → next stop of the same pattern |

On a boarding link:
- `num_trips` is the number of trains in 07:00–08:00.
- `vdf_fftt` = 30/`num_trips` minutes, which is half the headway, the expected wait under random arrivals.
- `vdf_cap` = 3,000 × `num_trips`.

## 4. Link and path: DTALite assignment and the path pool

**Assignment run.** `GMNS/run_dtalite.py` renumbers nodes (stations 1–50, service nodes from 1001) and links, then calls `DTALite.assignment()`. Its inputs are:
- `settings.csv`: 10 iterations, demand period 07–08;
- `mode_type.csv`: mode `transit`, demand file `OD_demand_7_Wed.csv`.

That demand file is the 07:00 hour of Wednesday 12 Feb 2025 (1,668 OD cells, 14,900 trips).

The output `route_assignment.csv` has one row per path:
- `o_zone_id`, `d_zone_id`: the OD pair;
- `link_ids`, `node_ids`: the path as a sequence of links and nodes;
- `prob`: the path share ω_{k|w}, which sums to 1 within an OD pair;
- `seed_od_volume`: the OD demand of that hour;
- `travel_time`, `distance`: the path cost.

It covers the 1,341 OD pairs that had demand in that hour (2,971 paths). Pairs with no feasible path are listed in `inaccessible_od.csv`.

> `run_dtalite.py` overwrites `node.csv` and `link.csv` in place, so run it on a copy of `GMNS/`. `run_dtalite_0219_2026.py` expects a `physical_stop_no` column that the shipped `node.csv` does not have; use `run_dtalite.py`.

**Path pool used in the paper.** `data/BART/column_pool/columns.csv` lists 4,898 candidate paths over all 2,450 OD markets (`path_id, o_zone_id, d_zone_id, link_sequence`). Each path contains exactly one boarding link, so the boarding resource of a path is unique.

## 5. From OD demand to arrivals at a boarding resource [§2.5, Eq. (9)]

For each path k:
- let η_{sk} = 1 if its boarding link is resource s;
- let ω_{k|w} be its share of OD market w.

The arrival rate at resource s in hour h is then

λ_{s,h} = Σ_w Σ_k η_{sk} ω_{k|w} y_{w,h}  (passengers per hour, since Δ_h = 1 h).

To obtain a station–direction stream for the loader, add up the patterns of one line-direction at one station.

`code/bart/bart_data_lineage.py` writes η and ω to `code/bart/output/path_boarding_incidence.csv` and works the MacArthur 08:00 example. The station total of 525.7 pax/h splits by line-direction as follows:

| Line-direction | Pax/h |
|---|---|
| Yellow-S | 317.1 |
| Red-S | 72.3 |
| Orange-S | 60.2 |
| Orange-N | 40.5 |
| Yellow-N | 23.8 |
| ODs with no path that hour | 11.8 |

**Two simplifications** to keep in mind:
- The shares ω come from one assigned hour and are applied to all hours.
- Transfers carry no time offset.

The paper's MacArthur check (Figure 12) treats the station total, all lines combined, as one stream served by a ten-minute headway.

## 6. The event loader: waiting, left behind, unused capacity [§2.2–2.4]

`code/evloader.py` turns an arrival rate λ(t) and an action (f, n) into passenger costs, one departure at a time:
- Departure k at time t_k has capacity C_k = κ n, with κ = 56.25 spaces per car (337.5 spaces for six cars, 450 for eight).
- Boarding is FIFO: b_k = min(waiting, C_k). Anyone not served stays in the queue Q, the *left-behind* passengers.
- Each hour's cost is c0·(ordinary waiting P⁰) + cQ·(backlog waiting Q) + cE·(unused spaces) + 2 per car-departure.

Two rules govern the timing of departures:
- Departures follow the headway 1/f of the action in force. A departure exactly at a stage boundary runs under the action of the stage it closes.
- After a change at time t0, the next departure is at max(t0, last departure + 1/f_new).

At 24:00 any remaining queue is cleared at no charge, but its waiting up to 24:00 is charged.

Run `python reproduce_boards.py` from `code/`. It prints 137.4 and 91.6 pax-h for the 08:00–09:00 hour (Figure 5), the backlog of about 988 at 10:00 (Figure 6), and the 08:00 keep/switch numbers (Figure 8).

> **Check yourself.** Why is backlog waiting Q not "half a headway"? Read Eq. (6) of the paper and compare the areas in Figure 6(b).

## 7. The within-day dynamic program [§3]

**Decision problem.** Choose a piecewise-constant plan of at most M stages (actions (f, n) from 7 options; changes only at whole hours) that minimizes the day's cost.

**Why it is a dynamic program.** The queue Q left at the end of one stage is the starting state of the next. The day therefore does not split into independent stages.

**Implementation** (`code/dayDP.py`, function `day_dp`): forward label setting over hours h = 0…23.

| DP element | In the code |
|---|---|
| Node | (number of stages so far m, action in force u, minutes since the last departure φ) |
| Label | (queue q, cost so far, plan) |
| Transition | keep u, or switch to v ≠ u if m + 1 ≤ M; simulate the hour with `simulate_segment` |
| Dominance | label 1 dominates label 2 at the same node if q1 ≤ q2 and C1 + cE (q2 − q1) ≤ C2 |
| Output | `best[m]`: the cheapest plan with exactly m stages |

The dominance test is the paper's Eq. (14). A smaller queue is worth at most cE per passenger, because each extra waiting passenger fills at most one otherwise-empty space later.

**Checks:**
- `python verify.py` enumerates all 64,729 plans with at most three stages and confirms that the DP finds the same optimum.
- `python curves.py` gives the exact-count costs J(m) and the lower convex hull of Figure 9. A fixed charge χ per change selects m stages only where m lies on that hull.
- `python contval.py` shows the continuation-value example (Table 3). At 08:00, switching saves 313.5 within the hour but loses over the day.

## 8. Nesting days: plans that stay for several days [§6]

Across days the state is:
- the plan in force;
- the number of plan changes j already made;
- the information available.

The queue is cleared every night. `code/s6_nested.py` computes Table 8 in five steps:
1. **Demand.** λ_d(h) = (1 − δ r(d)) × full(h) × (1 + ε_{d,h}), where r(d) = e^{−(d−1)/10.5}, the horizon is 30 days, and δ ∈ {0.30, 0.58, 0.80}. The noise ε is 2.5% hourly Gaussian noise, drawn with seed 19; every depth uses the same draws.
2. **Candidate pool.** Take every day's exact optimal plans with m = 1…5 stages, and remove duplicates. Allowance M keeps the plans with at most M stages.
3. **Block costs.** Evaluate every pool plan on every day.
4. **Across days.** Partition the 30 days exactly into at most N blocks, with one plan per block. This is a shortest path over (block count, day).
5. **Report.** Give the saving against the best single one-stage plan held for the whole recovery (M = N = 1).

The values are hindsight values, because the whole demand path is known in advance.

## 9. Newell checks on observed and thinner data [§7.2, §8]

**Newell's square-root rule.** Spread a fixed number of departures in proportion to √λ. The saving against uniform service is 1 − (Σ√λ)² / (H Σλ).
- `code/bart/bart_newell_systemwide.py` gives 8.7% on the BART weekday profile over hours 05–23.
- `code/bart/bart_macarthur.py` gives the event-based MacArthur check: 81.8 → 66.7 pax-h, an 18.4% saving.

**Thinner-data cases:**
- **Phoenix** (`code/phoenix/`). Only monthly boardings by station are available, so monthly OD is estimated with a production-constrained gravity model. The distance decay β is set so that the mean trip is about 7.2 km. The script reproduces Table D2 and the 1.37% and 0.11% savings.
- **Seattle RapidRide** (`code/king_county/`). Line-level AM boardings are spread over stops using the GTFS stop sequence. The script reproduces the 6.4% saving.

## 10. Exercises

1. Recompute the mean weekday total and CV with same-station records *included*. How much do they change?
2. Using `path_boarding_incidence.csv`, build the Yellow-S stream at MacArthur and redo the Figure 12 check for that line alone.
3. In `s6_nested.py`, set the noise to zero and compare Table 8 with the published table. Which cells move most?
4. Add a change charge χ_W to `day_dp`. At what χ does day 10 move from five stages to three? Compare with the hull break-even values printed by `curves.py`.
5. Move a transition off the whole-hour grid (for example, to 07:30). Use `code/tests/test_evloader_phase.py` to see how the departure phase rule works.
