#!/usr/bin/env python3
"""
Task 3.4 - Material Handling Fleet Sizing Model
===============================================
Computes the number of Automated Guided Vehicles required to satisfy a given
factory delivery demand.

Model (standard material-handling analysis, after Groover)
----------------------------------------------------------
For one delivery cycle a vehicle must

        load  ->  travel loaded  ->  unload  ->  travel empty back

so the DELIVERY CYCLE TIME is

        Tc = TL + Ld/Vc + TU + Le/Vc            [min per delivery]

            TL = loading time            [min]
            TU = unloading time          [min]
            Ld = loaded travel distance  [m]
            Le = empty travel distance   [m]
            Vc = vehicle speed           [m/min]

The WORKLOAD imposed on the fleet by a demand of Rf deliveries per hour is

        WL = Rf * Tc                            [min of vehicle work per hour]

A vehicle cannot work the full 60 minutes of an hour: it loses time to battery
charging and breakdowns (availability A) and to blocking, queueing and
congestion (traffic factor Ft <= 1).  The AVAILABLE TIME per vehicle is

        AT = 60 * A * Ft                        [min per hour per vehicle]

and the required fleet size is

        n  = WL / AT        rounded UP to the next whole vehicle

The traffic factor may either be supplied directly or estimated from the number
of vehicles sharing the guide path, which makes the calculation implicit - the
program then solves it by iteration.

Run:  python3 task3_4_agv_fleet_sizing.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, List


# ----------------------------------------------------------------------------
# 1. INPUT MODEL
# ----------------------------------------------------------------------------

@dataclass
class AGVSystem:
    """All inputs needed to size an AGV fleet."""
    name: str
    load_time: float            # TL [min]
    unload_time: float          # TU [min]
    loaded_distance: float      # Ld [m]
    empty_distance: float       # Le [m]
    velocity: float             # Vc [m/min]
    deliveries_per_hour: float  # Rf [deliveries/h]
    availability: float = 0.95  # A, fraction
    traffic_factor: Optional[float] = 0.90   # Ft; None -> estimate it

    def __post_init__(self) -> None:
        if self.velocity <= 0:
            raise ValueError("vehicle velocity must be positive")
        if not 0 < self.availability <= 1:
            raise ValueError("availability must lie in (0, 1]")
        if self.traffic_factor is not None and not 0 < self.traffic_factor <= 1:
            raise ValueError("traffic factor must lie in (0, 1]")


# ----------------------------------------------------------------------------
# 2. CORE CALCULATIONS
# ----------------------------------------------------------------------------

def delivery_cycle_time(s: AGVSystem) -> dict:
    """Break the delivery cycle into its four components [min]."""
    t_loaded = s.loaded_distance / s.velocity
    t_empty = s.empty_distance / s.velocity
    Tc = s.load_time + t_loaded + s.unload_time + t_empty
    return {"load": s.load_time, "travel_loaded": t_loaded,
            "unload": s.unload_time, "travel_empty": t_empty, "Tc": Tc}


def workload(s: AGVSystem, Tc: float) -> float:
    """Total vehicle-minutes of work demanded per hour."""
    return s.deliveries_per_hour * Tc


def available_time(s: AGVSystem, Ft: float) -> float:
    """Productive minutes available from ONE vehicle in one hour."""
    return 60.0 * s.availability * Ft


def estimate_traffic_factor(n_vehicles: float) -> float:
    """
    Simple congestion model when Ft is not supplied.
    A single vehicle has no interference (Ft = 1.0); each additional vehicle on
    the shared guide path costs roughly 5 % of the available time, with a floor
    of 0.60 so the estimate never becomes unphysical.
    """
    return max(0.60, 1.0 - 0.05 * max(0.0, n_vehicles - 1.0))


def fleet_size(s: AGVSystem, max_iter: int = 50) -> dict:
    """
    Compute the required fleet size.
    If traffic_factor is None the calculation is implicit (Ft depends on n and n
    depends on Ft) and is solved by fixed-point iteration.
    """
    cyc = delivery_cycle_time(s)
    Tc = cyc["Tc"]
    WL = workload(s, Tc)

    if s.traffic_factor is not None:
        Ft = s.traffic_factor
        n_exact = WL / available_time(s, Ft)
        iterations = 1
    else:
        Ft, n_exact, iterations = 1.0, WL / available_time(s, 1.0), 0
        for iterations in range(1, max_iter + 1):
            Ft_new = estimate_traffic_factor(math.ceil(n_exact))
            n_new = WL / available_time(s, Ft_new)
            if abs(n_new - n_exact) < 1e-6 and abs(Ft_new - Ft) < 1e-9:
                Ft, n_exact = Ft_new, n_new
                break
            Ft, n_exact = Ft_new, n_new

    n_req = math.ceil(n_exact - 1e-9)
    AT = available_time(s, Ft)
    utilisation = n_exact / n_req if n_req else 0.0

    return {**cyc, "WL": WL, "Ft": Ft, "AT": AT,
            "n_exact": n_exact, "n_required": n_req,
            "utilisation": utilisation, "iterations": iterations,
            "achievable_rate": n_req * AT / Tc}


# ----------------------------------------------------------------------------
# 3. REPORTING
# ----------------------------------------------------------------------------

def report(s: AGVSystem, r: dict) -> None:
    print("=" * 80)
    print(f"AGV FLEET SIZING  -  {s.name}")
    print("=" * 80)
    print("  INPUTS")
    print(f"    Loading time        TL = {s.load_time:8.3f} min")
    print(f"    Unloading time      TU = {s.unload_time:8.3f} min")
    print(f"    Loaded distance     Ld = {s.loaded_distance:8.1f} m")
    print(f"    Empty distance      Le = {s.empty_distance:8.1f} m")
    print(f"    Vehicle speed       Vc = {s.velocity:8.1f} m/min")
    print(f"    Demand              Rf = {s.deliveries_per_hour:8.1f} deliveries/h")
    print(f"    Availability        A  = {s.availability:8.3f}")
    print(f"    Traffic factor      Ft = "
          f"{'estimated' if s.traffic_factor is None else f'{s.traffic_factor:8.3f}'}")
    print("-" * 80)
    print("  DELIVERY CYCLE TIME")
    print(f"    Load                      = {r['load']:8.3f} min")
    print(f"    Travel loaded  Ld/Vc      = {r['travel_loaded']:8.3f} min")
    print(f"    Unload                    = {r['unload']:8.3f} min")
    print(f"    Travel empty   Le/Vc      = {r['travel_empty']:8.3f} min")
    print(f"    ------------------------------------")
    print(f"    Tc                        = {r['Tc']:8.3f} min per delivery")
    print("-" * 80)
    print("  FLEET CALCULATION")
    print(f"    Workload   WL = Rf x Tc            = {r['WL']:8.3f} vehicle-min per hour")
    print(f"    Traffic factor actually used  Ft   = {r['Ft']:8.3f}"
          f"{'   (converged in %d iterations)' % r['iterations'] if s.traffic_factor is None else ''}")
    print(f"    Available time AT = 60 x A x Ft    = {r['AT']:8.3f} min per vehicle per hour")
    print(f"    Vehicles  n = WL / AT              = {r['n_exact']:8.3f}")
    print(f"    >>> REQUIRED FLEET SIZE            = {r['n_required']:5d} AGVs  (rounded up)")
    print(f"    Fleet utilisation                  = {r['utilisation']*100:8.1f} %")
    print(f"    Rate the fleet can actually serve  = {r['achievable_rate']:8.2f} deliveries/h"
          f"   (demand {s.deliveries_per_hour:.1f}/h)")
    print("=" * 80 + "\n")


# ----------------------------------------------------------------------------
# 4. TEST CASES
# ----------------------------------------------------------------------------

def main() -> None:
    print("\n" + "#" * 80)
    print("# TASK 3.4 - AGV FLEET SIZING MODEL : TEST VERIFICATION RUN")
    print("#" * 80 + "\n")

    cases: List[AGVSystem] = []

    # TEST CASE 1 - the FMC loop of Assignment 1 (raw store -> CNC cell)
    cases.append(AGVSystem(
        name="TEST CASE 1 - FMC raw-material loop (Assignment 1 cell)",
        load_time=0.60, unload_time=0.50,
        loaded_distance=140.0, empty_distance=110.0,
        velocity=50.0, deliveries_per_hour=22.0,
        availability=0.95, traffic_factor=0.90))

    # TEST CASE 2 - heavy demand, slow vehicle, congested path
    cases.append(AGVSystem(
        name="TEST CASE 2 - High-demand assembly feed (congested)",
        load_time=1.00, unload_time=0.75,
        loaded_distance=320.0, empty_distance=280.0,
        velocity=40.0, deliveries_per_hour=35.0,
        availability=0.90, traffic_factor=0.85))

    # TEST CASE 3 - traffic factor NOT given, solved implicitly
    cases.append(AGVSystem(
        name="TEST CASE 3 - Traffic factor estimated by iteration",
        load_time=0.75, unload_time=0.75,
        loaded_distance=200.0, empty_distance=150.0,
        velocity=45.0, deliveries_per_hour=40.0,
        availability=0.92, traffic_factor=None))

    results = []
    for s in cases:
        r = fleet_size(s)
        report(s, r)
        results.append((s, r))

        # ---- verification assertions ------------------------------------
        manual_Tc = (s.load_time + s.loaded_distance / s.velocity
                     + s.unload_time + s.empty_distance / s.velocity)
        assert abs(r["Tc"] - manual_Tc) < 1e-9, "cycle time does not match the hand formula"
        assert abs(r["WL"] - s.deliveries_per_hour * manual_Tc) < 1e-9, "workload mismatch"
        assert r["n_required"] >= r["n_exact"] - 1e-9, "fleet size was not rounded UP"
        assert r["n_required"] - r["n_exact"] < 1.0, "rounded up by more than one vehicle"
        assert r["achievable_rate"] >= s.deliveries_per_hour - 1e-6, \
            "the chosen fleet cannot meet the demand"
        assert 0 < r["utilisation"] <= 1.0 + 1e-9, "utilisation out of range"
        print("   >>> SANITY CHECKS PASSED for this case\n")

    # ---- an extra check: demand sweep must give a monotonic fleet size -----
    print("=" * 80)
    print("MONOTONICITY CHECK - fleet size against rising demand (case 1 geometry)")
    print("=" * 80)
    base = cases[0]
    print(f"{'Demand, deliveries/h':>22}{'n exact':>12}{'AGVs required':>16}")
    prev = 0
    for rf in (5, 10, 20, 30, 40, 60, 80):
        s = AGVSystem(name="sweep", load_time=base.load_time, unload_time=base.unload_time,
                      loaded_distance=base.loaded_distance, empty_distance=base.empty_distance,
                      velocity=base.velocity, deliveries_per_hour=rf,
                      availability=base.availability, traffic_factor=base.traffic_factor)
        rr = fleet_size(s)
        print(f"{rf:>22.0f}{rr['n_exact']:>12.3f}{rr['n_required']:>16d}")
        assert rr["n_required"] >= prev, "fleet size must not fall as demand rises"
        prev = rr["n_required"]
    print("   >>> fleet size rises monotonically with demand\n")

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'Case':<56}{'Tc,min':>9}{'AGVs':>7}")
    for s, r in results:
        print(f"{s.name:<56}{r['Tc']:>9.3f}{r['n_required']:>7d}")
    print("=" * 80)
    print("ALL TEST CASES COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
