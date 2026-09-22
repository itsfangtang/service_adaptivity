# Section 3 (v25) computations

New event-based computations for Section 3, written for the v25 manuscript (10 Sept 2026).
Demand: the archived modeled 30x24 recovery matrix (`demo_sensor_demand_30x24.csv`,
from `BART_YellowLine_Nested_DP/demo_output`); not observed BART counts.

    python make_demand.py        # CSV -> demand.npy
    python reproduce_boards.py   # loader reproduces Board 2, 3 and 16 numbers exactly
    python verify.py             # exact DP == complete enumeration for M<=3 (64,729 plans), c_E in {1,0}
    python dayDP.py 9            # J*(M) for day 10, M<=5
    python contval.py            # 08:00 keep/switch continuation values (Table 6)
    python curves.py             # exact-count J_0^{=}(m), m<=8, days 1,10,20,30 -> curves.json
    python fig_curves.py         # Figure 7

Conventions (Section 2 v25): FIFO; departures continue from the last departure with the
headway of the action in force; a departure at a boundary belongs to the interval it
closes; transitions only at whole hours; passengers left at 24:00 cleared at zero
operating charge (none remained in any computed day). Weights: c0=cQ=1 per pax-h,
cE=1 (base) or 0 per unused space, 2 per car-departure; kappa=56.25 spaces/car.
Label dominance: q1<=q2 and C1+cE*(q2-q1)<=C2 (Section 3, Eq. dominance).

    python s4_partition.py       # Table 6 (Section 4.1)
    python s4_drift.py           # Table 7 / Appendix A.2 checks
