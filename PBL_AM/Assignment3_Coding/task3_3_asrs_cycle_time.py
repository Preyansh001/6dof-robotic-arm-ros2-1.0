#!/usr/bin/env python3
"""
Task 3.3 - AS/RS Single- and Dual-Command Cycle Time Algorithm
=============================================================
Engineering analysis of a single-rack (one aisle, one S/R machine) Automated
Storage & Retrieval System.  The program computes single-command (SC) and
dual-command (DC) travel cycle times and the resulting throughput for

    * RANDOMIZED storage  - analytical Bozer & White model, and
    * DEDICATED storage   - explicit travel to named rack locations.

Theory
------
The S/R machine drives its horizontal (y) and vertical (z) axes SIMULTANEOUSLY,
so the travel time between two points is the CHEBYSHEV time

        t = max( dy / Vy , dz / Vz )

Define the time to reach the far corner of the rack along each axis

        th = L / Vy        tv = H / Vz
        T  = max(th, tv)                      scaling factor
        b  = min(th, tv) / T                  rack shape factor, 0 < b <= 1

For randomized storage with the input/output point at one lower corner, Bozer
and White give the expected travel times

        E(SC) = T * ( 1 + b^2 / 3 )
        E(DC) = T * ( 4/3 + b^2 / 2 - b^3 / 30 )

E(SC) is a complete round trip (I/O point -> location -> I/O point).
E(DC) covers I/O -> storage location -> retrieval location -> I/O.

Adding the pick-and-deposit (P/D) time tpd:

        SC cycle = E(SC) + 2 * tpd          -> 1 transaction
        DC cycle = E(DC) + 4 * tpd          -> 2 transactions

The analytical SC result is re-derived inside this program by Monte-Carlo
simulation, which is used as an independent verification of the formula.

Run:  python3 task3_3_asrs_cycle_time.py
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Tuple, List


# ----------------------------------------------------------------------------
# 1. SYSTEM DEFINITION
# ----------------------------------------------------------------------------

@dataclass
class ASRS:
    """Geometry and kinematics of one AS/RS aisle."""
    name: str
    rack_length: float          # L [m]
    rack_height: float          # H [m]
    v_horizontal: float         # Vy [m/s]
    v_vertical: float           # Vz [m/s]
    tpd: float                  # pick-and-deposit time per operation [s]
    availability: float = 1.0   # fraction of the hour the machine is available

    # ---- derived quantities -------------------------------------------------
    @property
    def th(self) -> float:
        """Time to traverse the full rack LENGTH [s]."""
        return self.rack_length / self.v_horizontal

    @property
    def tv(self) -> float:
        """Time to traverse the full rack HEIGHT [s]."""
        return self.rack_height / self.v_vertical

    @property
    def T(self) -> float:
        """Scaling factor T = max(th, tv) [s]."""
        return max(self.th, self.tv)

    @property
    def b(self) -> float:
        """Shape factor b = min(th,tv)/T, 0 < b <= 1 (b = 1 is a square-in-time rack)."""
        return min(self.th, self.tv) / self.T

    def travel_time(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Chebyshev travel time between two (y, z) rack positions [s]."""
        return max(abs(p2[0] - p1[0]) / self.v_horizontal,
                   abs(p2[1] - p1[1]) / self.v_vertical)


# ----------------------------------------------------------------------------
# 2. RANDOMIZED STORAGE - ANALYTICAL MODEL
# ----------------------------------------------------------------------------

def sc_travel_random(s: ASRS) -> float:
    """Expected SINGLE-COMMAND travel time, randomized storage [s]."""
    return s.T * (1.0 + s.b ** 2 / 3.0)


def dc_travel_random(s: ASRS) -> float:
    """Expected DUAL-COMMAND travel time, randomized storage [s]."""
    return s.T * (4.0 / 3.0 + s.b ** 2 / 2.0 - s.b ** 3 / 30.0)


def sc_cycle_random(s: ASRS) -> float:
    """Complete SC cycle time including P/D handling [s]."""
    return sc_travel_random(s) + 2.0 * s.tpd


def dc_cycle_random(s: ASRS) -> float:
    """Complete DC cycle time including P/D handling [s]."""
    return dc_travel_random(s) + 4.0 * s.tpd


def throughput(s: ASRS, cycle_s: float, transactions_per_cycle: int) -> float:
    """Transactions per hour for a given cycle time."""
    if cycle_s <= 0:
        return 0.0
    return 3600.0 * s.availability * transactions_per_cycle / cycle_s


# ----------------------------------------------------------------------------
# 3. RANDOMIZED STORAGE - MONTE-CARLO VERIFICATION
# ----------------------------------------------------------------------------

def sc_travel_monte_carlo(s: ASRS, n: int = 400_000, seed: int = 12345) -> float:
    """
    Independent estimate of E(SC) by simulation.
    A storage location is drawn uniformly over the rack face and the machine
    makes a round trip from the I/O point at the lower corner (0, 0).
    """
    rng = random.Random(seed)
    total = 0.0
    for _ in range(n):
        y = rng.uniform(0.0, s.rack_length)
        z = rng.uniform(0.0, s.rack_height)
        total += 2.0 * s.travel_time((0.0, 0.0), (y, z))
    return total / n


def dc_travel_monte_carlo(s: ASRS, n: int = 400_000, seed: int = 999) -> float:
    """
    Independent estimate of E(DC): I/O -> store at P1 -> travel to P2 -> I/O.
    Both locations are drawn uniformly and independently.
    """
    rng = random.Random(seed)
    total = 0.0
    io = (0.0, 0.0)
    for _ in range(n):
        p1 = (rng.uniform(0, s.rack_length), rng.uniform(0, s.rack_height))
        p2 = (rng.uniform(0, s.rack_length), rng.uniform(0, s.rack_height))
        total += (s.travel_time(io, p1) + s.travel_time(p1, p2) + s.travel_time(p2, io))
    return total / n


# ----------------------------------------------------------------------------
# 4. DEDICATED STORAGE - EXPLICIT LOCATIONS
# ----------------------------------------------------------------------------

@dataclass
class Location:
    """A named, dedicated rack location."""
    label: str
    y: float            # distance along the rack [m]
    z: float            # height [m]

    def as_tuple(self) -> Tuple[float, float]:
        return (self.y, self.z)


def sc_cycle_dedicated(s: ASRS, loc: Location) -> float:
    """SC cycle to one dedicated location (round trip + 2 P/D) [s]."""
    return 2.0 * s.travel_time((0.0, 0.0), loc.as_tuple()) + 2.0 * s.tpd


def dc_cycle_dedicated(s: ASRS, store: Location, retrieve: Location) -> float:
    """DC cycle: I/O -> store -> retrieve -> I/O, plus 4 P/D [s]."""
    io = (0.0, 0.0)
    t = (s.travel_time(io, store.as_tuple())
         + s.travel_time(store.as_tuple(), retrieve.as_tuple())
         + s.travel_time(retrieve.as_tuple(), io))
    return t + 4.0 * s.tpd


# ----------------------------------------------------------------------------
# 5. REPORTING
# ----------------------------------------------------------------------------

def analyse(s: ASRS, locations: List[Location] | None = None,
            monte_carlo: bool = True) -> dict:
    print("=" * 84)
    print(f"AS/RS CYCLE-TIME ANALYSIS  -  {s.name}")
    print("=" * 84)
    print(f"  Rack length  L   = {s.rack_length:8.2f} m      Horizontal speed Vy = {s.v_horizontal:5.2f} m/s")
    print(f"  Rack height  H   = {s.rack_height:8.2f} m      Vertical speed   Vz = {s.v_vertical:5.2f} m/s")
    print(f"  P/D time     tpd = {s.tpd:8.2f} s      Availability        = {s.availability*100:5.1f} %")
    print("-" * 84)
    print(f"  th = L/Vy = {s.th:6.2f} s        tv = H/Vz = {s.tv:6.2f} s")
    print(f"  T  = max(th,tv) = {s.T:6.2f} s    b = min/T = {s.b:6.4f}")
    print("-" * 84)

    e_sc, e_dc = sc_travel_random(s), dc_travel_random(s)
    c_sc, c_dc = sc_cycle_random(s), dc_cycle_random(s)
    r_sc = throughput(s, c_sc, 1)
    r_dc = throughput(s, c_dc, 2)

    print("  RANDOMIZED STORAGE (Bozer & White)")
    print(f"    E(SC) travel      = T(1 + b^2/3)             = {e_sc:8.2f} s")
    print(f"    E(DC) travel      = T(4/3 + b^2/2 - b^3/30)  = {e_dc:8.2f} s")
    print(f"    SC cycle  (+2 tpd)                           = {c_sc:8.2f} s   -> {r_sc:7.1f} transactions/h")
    print(f"    DC cycle  (+4 tpd)                           = {c_dc:8.2f} s   -> {r_dc:7.1f} transactions/h")
    print(f"    Throughput gain of dual over single command  = {(r_dc/r_sc - 1)*100:6.1f} %")

    out = {"T": s.T, "b": s.b, "E_SC": e_sc, "E_DC": e_dc,
           "SC_cycle": c_sc, "DC_cycle": c_dc, "R_SC": r_sc, "R_DC": r_dc}

    if monte_carlo:
        mc_sc = sc_travel_monte_carlo(s)
        mc_dc = dc_travel_monte_carlo(s)
        esc = abs(mc_sc - e_sc) / e_sc * 100
        edc = abs(mc_dc - e_dc) / e_dc * 100
        print("-" * 84)
        print("  MONTE-CARLO VERIFICATION OF THE ANALYTICAL FORMULAE (400 000 trials)")
        print(f"    E(SC): analytical {e_sc:7.3f} s   simulated {mc_sc:7.3f} s   deviation {esc:5.2f} %")
        print(f"    E(DC): analytical {e_dc:7.3f} s   simulated {mc_dc:7.3f} s   deviation {edc:5.2f} %")
        assert esc < 1.0, "SC model does not agree with the simulation"
        assert edc < 1.0, "DC model does not agree with the simulation"
        print("    >>> both models agree with the simulation to better than 1 %")
        out["MC_SC"], out["MC_DC"] = mc_sc, mc_dc

    if locations:
        print("-" * 84)
        print("  DEDICATED STORAGE - named locations")
        print(f"    {'Location':<14}{'y, m':>8}{'z, m':>8}{'SC cycle, s':>14}{'SC rate, /h':>14}")
        for loc in locations:
            c = sc_cycle_dedicated(s, loc)
            print(f"    {loc.label:<14}{loc.y:>8.2f}{loc.z:>8.2f}{c:>14.2f}{3600.0*s.availability/c:>14.1f}")
        if len(locations) >= 2:
            d = dc_cycle_dedicated(s, locations[0], locations[1])
            print(f"    DC cycle  {locations[0].label} (store) -> {locations[1].label} (retrieve)"
                  f" = {d:.2f} s  -> {2*3600.0*s.availability/d:.1f} transactions/h")
            out["DC_dedicated"] = d
    print("=" * 84 + "\n")
    return out


# ----------------------------------------------------------------------------
# 6. TEST CASES
# ----------------------------------------------------------------------------

def main() -> None:
    print("\n" + "#" * 84)
    print("# TASK 3.3 - AS/RS CYCLE TIME ALGORITHM : TEST VERIFICATION RUN")
    print("#" * 84 + "\n")

    # ---- TEST CASE 1 : tall narrow rack, vertical axis dominates -------------
    c1 = ASRS(name="TEST CASE 1 - Tall unit-load rack (vertical dominant)",
              rack_length=60.0, rack_height=18.0,
              v_horizontal=2.0, v_vertical=0.5, tpd=15.0, availability=0.95)
    locs1 = [Location("A-01-01", 3.0, 1.2), Location("A-30-08", 45.0, 14.4),
             Location("A-20-05", 30.0, 9.0)]
    r1 = analyse(c1, locs1)
    assert 0 < c1.b <= 1.0, "shape factor out of range"
    assert r1["DC_cycle"] > r1["SC_cycle"], "a DC cycle must take longer than an SC cycle"
    assert r1["R_DC"] > r1["R_SC"], "DC must give a higher throughput"

    # ---- TEST CASE 2 : long low rack, horizontal axis dominates --------------
    c2 = ASRS(name="TEST CASE 2 - Long mini-load rack (horizontal dominant)",
              rack_length=90.0, rack_height=6.0,
              v_horizontal=1.2, v_vertical=0.8, tpd=8.0, availability=0.90)
    locs2 = [Location("B-05-02", 12.0, 2.0), Location("B-40-06", 72.0, 5.0)]
    r2 = analyse(c2, locs2)
    assert abs(c2.th - 75.0) < 1e-9, "th calculation is wrong"
    assert abs(c2.tv - 7.5) < 1e-9, "tv calculation is wrong"
    assert abs(c2.T - 75.0) < 1e-9 and abs(c2.b - 0.1) < 1e-9, "T/b calculation is wrong"

    # ---- TEST CASE 3 : square-in-time rack, b = 1 ---------------------------
    #  L/Vy = H/Vz exactly, so b = 1 and the formulae take their maximum values
    c3 = ASRS(name="TEST CASE 3 - Square-in-time rack (b = 1, limiting case)",
              rack_length=40.0, rack_height=10.0,
              v_horizontal=2.0, v_vertical=0.5, tpd=10.0, availability=1.0)
    r3 = analyse(c3, [Location("C-01-01", 0.0, 0.0), Location("C-MAX", 40.0, 10.0)])
    assert abs(c3.b - 1.0) < 1e-9, "this rack should be square in time (b = 1)"
    # with b = 1 : E(SC) = T*4/3 and E(DC) = T*(4/3 + 1/2 - 1/30)
    assert abs(r3["E_SC"] - c3.T * 4.0 / 3.0) < 1e-9, "b=1 SC limit is wrong"
    assert abs(r3["E_DC"] - c3.T * (4.0/3.0 + 0.5 - 1.0/30.0)) < 1e-9, "b=1 DC limit is wrong"
    print("   >>> b = 1 limiting values confirmed analytically\n")

    print("=" * 84)
    print("SUMMARY")
    print("=" * 84)
    print(f"{'Case':<52}{'b':>7}{'SC,s':>9}{'DC,s':>9}{'DC rate/h':>12}")
    for s, r in ((c1, r1), (c2, r2), (c3, r3)):
        print(f"{s.name:<52}{r['b']:>7.4f}{r['SC_cycle']:>9.2f}{r['DC_cycle']:>9.2f}{r['R_DC']:>12.1f}")
    print("=" * 84)
    print("ALL TEST CASES COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
