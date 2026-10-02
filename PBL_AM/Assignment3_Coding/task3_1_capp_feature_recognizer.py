#!/usr/bin/env python3
"""
Task 3.1 - Generative CAPP Feature Recognizer
=============================================
Accepts the feature parameters of a turned component (stock diameter, the final
turned steps, chamfer angle, thread pitch) and automatically generates:

    * the ordered machining sequence,
    * the cutting tool selected for every operation,
    * cutting speed (Vc), spindle speed (N) and feed (f),
    * depth of cut and the number of passes,
    * the estimated machining time for each operation and for the whole part.

Method
------
1.  FEATURE RECOGNITION - the input geometry is scanned and classified into
    machinable features (face, cylindrical step, chamfer, groove, thread,
    parting face).
2.  OPERATION SEQUENCING - features are ordered by the standard turning
    precedence rules held in PRECEDENCE (face first, roughing before
    finishing, thread after its relief groove, part-off last).
3.  TOOL + CUTTING DATA SELECTION - a tool is chosen per operation from
    TOOL_LIBRARY and the cutting data is looked up from CUTTING_DATA, which is
    indexed by (work material, operation class).
4.  PROCESS CALCULATION -
        N  = 1000 * Vc / (pi * D)                    [rev/min]
        t  = L / (f * N)   per pass                  [min]
        passes_rough = ceil(radial stock / ap)

Run:  python3 task3_1_capp_feature_recognizer.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ----------------------------------------------------------------------------
# 1. KNOWLEDGE BASE
# ----------------------------------------------------------------------------

# Cutting data: {material: {operation class: (Vc m/min, f mm/rev, ap mm)}}
# Values are representative of uncoated/coated carbide tooling on a rigid CNC
# turning centre and are deliberately conservative.
CUTTING_DATA: Dict[str, Dict[str, tuple]] = {
    "MILD_STEEL":  {"FACE": (180, 0.20, 1.0), "ROUGH": (200, 0.30, 2.5),
                    "FINISH": (260, 0.12, 0.4), "GROOVE": (120, 0.08, 2.0),
                    "THREAD": (100, None, None), "PART_OFF": (110, 0.07, 2.5),
                    "CHAMFER": (220, 0.10, 0.5)},
    "ALLOY_STEEL": {"FACE": (140, 0.18, 1.0), "ROUGH": (160, 0.25, 2.0),
                    "FINISH": (200, 0.10, 0.3), "GROOVE": (90,  0.06, 2.0),
                    "THREAD": (80,  None, None), "PART_OFF": (85, 0.06, 2.5),
                    "CHAMFER": (180, 0.08, 0.5)},
    "ALUMINIUM":   {"FACE": (500, 0.25, 1.5), "ROUGH": (600, 0.35, 3.0),
                    "FINISH": (800, 0.15, 0.5), "GROOVE": (300, 0.10, 2.0),
                    "THREAD": (200, None, None), "PART_OFF": (250, 0.10, 2.5),
                    "CHAMFER": (700, 0.12, 0.5)},
    "STAINLESS":   {"FACE": (110, 0.15, 0.8), "ROUGH": (120, 0.20, 1.5),
                    "FINISH": (150, 0.09, 0.3), "GROOVE": (70,  0.05, 1.5),
                    "THREAD": (60,  None, None), "PART_OFF": (65, 0.05, 2.0),
                    "CHAMFER": (140, 0.07, 0.4)},
}

# Tool library: {operation class: (station, ISO designation, description)}
TOOL_LIBRARY: Dict[str, tuple] = {
    "FACE":     ("T0101", "DCLNR 2525 M12 + CNMG 120408-PR", "95 deg right-hand facing/turning tool, 0.8 mm nose"),
    "ROUGH":    ("T0101", "DCLNR 2525 M12 + CNMG 120408-PR", "95 deg right-hand roughing tool, 0.8 mm nose"),
    "FINISH":   ("T0202", "SDJCR 2525 M11 + DCMT 11T304-PF", "93 deg right-hand finishing tool, 0.4 mm nose"),
    "CHAMFER":  ("T0202", "SDJCR 2525 M11 + DCMT 11T304-PF", "finishing tool used at 45 deg for chamfering"),
    "GROOVE":   ("T0303", "QD-LCH 2525 + QD-NH-0300", "3 mm parting/grooving blade"),
    "THREAD":   ("T0404", "SER 2525 M16 + 16ER AG60", "60 deg external threading insert"),
    "PART_OFF": ("T0303", "QD-LCH 2525 + QD-NH-0300", "3 mm parting blade"),
}

# Operation precedence - lower number is machined first.
PRECEDENCE: Dict[str, int] = {
    "FACE": 10, "ROUGH": 20, "GROOVE": 30, "FINISH": 40,
    "CHAMFER": 50, "THREAD": 60, "PART_OFF": 70,
}

# Thread infeed schedule: number of passes as a function of pitch (ISO metric).
THREAD_PASSES = {0.5: 5, 0.75: 6, 1.0: 7, 1.25: 8, 1.5: 9, 1.75: 10, 2.0: 11, 2.5: 13, 3.0: 15}


# ----------------------------------------------------------------------------
# 2. INPUT DATA MODEL
# ----------------------------------------------------------------------------

@dataclass
class Step:
    """One cylindrical step of the finished component."""
    diameter: float          # finished diameter [mm]
    length: float            # axial length of this step [mm]


@dataclass
class PartSpec:
    """Complete description of the turned component to be planned."""
    name: str
    material: str                       # key into CUTTING_DATA
    stock_diameter: float               # bar diameter [mm]
    stock_length: float                 # length of bar used per piece [mm]
    steps: List[Step]                   # ordered from the free (chuck-remote) end
    facing_allowance: float = 1.0       # material removed when facing [mm]
    chamfer_size: float = 0.0           # chamfer leg length [mm], 0 = none
    chamfer_angle: float = 45.0         # chamfer angle [deg]
    thread_pitch: float = 0.0           # 0 = no thread
    thread_length: float = 0.0          # threaded length [mm]
    thread_on_step: int = 0             # index into steps that carries the thread
    groove_width: float = 0.0           # thread relief groove, 0 = none
    groove_depth: float = 0.0
    max_spindle_rpm: float = 3500.0     # machine limit
    max_constant_surface_rpm: float = 3500.0
    rapid_time_per_op: float = 0.08     # approach/retract allowance per op [min]


@dataclass
class Operation:
    """One planned operation, fully costed."""
    seq: int
    name: str
    op_class: str
    tool_station: str
    tool_desc: str
    diameter: float          # diameter used for the speed calculation [mm]
    Vc: float                # cutting speed [m/min]
    N: float                 # spindle speed [rev/min]
    feed: float              # feed [mm/rev]
    ap: Optional[float]      # depth of cut [mm]
    passes: int
    length: float            # cut length per pass [mm]
    time_min: float          # machining time including approach [min]
    note: str = ""


# ----------------------------------------------------------------------------
# 3. PROCESS CALCULATIONS
# ----------------------------------------------------------------------------

def spindle_speed(Vc: float, diameter: float, limit: float) -> float:
    """N = 1000*Vc / (pi*D), clamped to the machine maximum."""
    if diameter <= 0:
        return limit
    return min(1000.0 * Vc / (math.pi * diameter), limit)


def cut_time(length: float, feed: float, N: float) -> float:
    """Machining time for one pass, t = L / (f * N)  [min]."""
    if feed <= 0 or N <= 0:
        return 0.0
    return length / (feed * N)


def thread_pass_count(pitch: float) -> int:
    """Number of infeed passes for a given ISO metric pitch."""
    if pitch in THREAD_PASSES:
        return THREAD_PASSES[pitch]
    # linear interpolation / extrapolation for non-tabulated pitches
    return max(4, int(round(4.0 + 3.6 * pitch)))


# ----------------------------------------------------------------------------
# 4. THE PLANNER
# ----------------------------------------------------------------------------

def recognise_features(part: PartSpec) -> List[dict]:
    """Classify the input geometry into machinable features."""
    feats: List[dict] = []

    feats.append({"cls": "FACE", "name": "Face the bar end",
                  "D": part.stock_diameter, "L": part.stock_diameter / 2.0,
                  "stock": part.facing_allowance})

    # Each finished step that is smaller than the stock needs roughing + finishing.
    z_from_end = 0.0
    for i, st in enumerate(part.steps):
        radial_stock = (part.stock_diameter - st.diameter) / 2.0
        if radial_stock > 0.01:
            feats.append({"cls": "ROUGH", "name": f"Rough turn step {i+1} to ø{st.diameter:.1f}",
                          "D": part.stock_diameter, "L": st.length + z_from_end,
                          "stock": radial_stock, "D_final": st.diameter})
        z_from_end += st.length

    z_from_end = 0.0
    for i, st in enumerate(part.steps):
        if (part.stock_diameter - st.diameter) / 2.0 > 0.01:
            feats.append({"cls": "FINISH", "name": f"Finish turn step {i+1} to ø{st.diameter:.1f}",
                          "D": st.diameter, "L": st.length + z_from_end, "stock": 0.0})
        z_from_end += st.length

    if part.groove_width > 0:
        gd = part.steps[part.thread_on_step].diameter
        feats.append({"cls": "GROOVE", "name": "Thread relief groove",
                      "D": gd, "L": part.groove_depth, "stock": part.groove_depth,
                      "width": part.groove_width})

    if part.chamfer_size > 0:
        d0 = part.steps[0].diameter
        feats.append({"cls": "CHAMFER", "name": f"Chamfer {part.chamfer_size}x{part.chamfer_angle:.0f}°",
                      "D": d0, "L": part.chamfer_size / math.sin(math.radians(part.chamfer_angle)),
                      "stock": 0.0})

    if part.thread_pitch > 0:
        td = part.steps[part.thread_on_step].diameter
        feats.append({"cls": "THREAD",
                      "name": f"Thread M{td:.0f}x{part.thread_pitch} over {part.thread_length} mm",
                      "D": td, "L": part.thread_length, "stock": 0.0,
                      "pitch": part.thread_pitch})

    feats.append({"cls": "PART_OFF", "name": "Part off component",
                  "D": part.steps[-1].diameter if part.steps else part.stock_diameter,
                  "L": (part.steps[-1].diameter if part.steps else part.stock_diameter) / 2.0,
                  "stock": 0.0})
    return feats


def plan(part: PartSpec) -> List[Operation]:
    """Generate the complete, ordered and costed process plan."""
    if part.material not in CUTTING_DATA:
        raise ValueError(f"No cutting data for material '{part.material}'. "
                         f"Known: {sorted(CUTTING_DATA)}")

    feats = recognise_features(part)
    # stable sort by the precedence rules
    feats.sort(key=lambda f: PRECEDENCE[f["cls"]])

    data = CUTTING_DATA[part.material]
    ops: List[Operation] = []

    for i, f in enumerate(feats, start=1):
        cls = f["cls"]
        Vc, feed, ap = data[cls]
        station, iso, desc = TOOL_LIBRARY[cls]
        note = ""

        if cls == "THREAD":
            pitch = f["pitch"]
            passes = thread_pass_count(pitch)
            feed = pitch                     # threading feed always equals the pitch
            N = spindle_speed(Vc, f["D"], part.max_spindle_rpm)
            t = passes * cut_time(f["L"] + 4.0 * pitch, feed, N)   # +run-in/run-out
            note = f"{passes} infeed passes, feed = pitch = {pitch} mm/rev"
            ap_used = None
        elif cls == "ROUGH":
            passes = max(1, math.ceil(f["stock"] / ap))
            # Speed is computed on the mean diameter actually being cut.
            d_mean = (f["D"] + f.get("D_final", f["D"])) / 2.0
            N = spindle_speed(Vc, d_mean, part.max_spindle_rpm)
            t = passes * cut_time(f["L"], feed, N)
            note = f"radial stock {f['stock']:.2f} mm / ap {ap} mm"
            ap_used = ap
        elif cls == "FACE":
            passes = max(1, math.ceil(f["stock"] / ap))
            N = spindle_speed(Vc, f["D"], part.max_spindle_rpm)
            t = passes * cut_time(f["L"], feed, N)
            note = "G94 facing cycle, constant surface speed recommended"
            ap_used = ap
        elif cls == "GROOVE":
            passes = max(1, math.ceil(f["width"] / 3.0))   # 3 mm wide blade
            N = spindle_speed(Vc, f["D"], part.max_spindle_rpm)
            t = passes * cut_time(f["L"], feed, N)
            note = f"groove {f['width']} mm wide x {f['stock']} mm deep"
            ap_used = f["stock"]
        else:                                 # FINISH, CHAMFER, PART_OFF
            passes = 1
            N = spindle_speed(Vc, f["D"], part.max_spindle_rpm)
            t = cut_time(f["L"], feed, N)
            ap_used = ap

        ops.append(Operation(seq=i, name=f["name"], op_class=cls,
                             tool_station=station, tool_desc=f"{iso} - {desc}",
                             diameter=f["D"], Vc=Vc, N=N, feed=feed, ap=ap_used,
                             passes=passes, length=f["L"],
                             time_min=t + part.rapid_time_per_op, note=note))
    return ops


# ----------------------------------------------------------------------------
# 5. REPORTING
# ----------------------------------------------------------------------------

def print_plan(part: PartSpec, ops: List[Operation]) -> float:
    print("=" * 100)
    print(f"GENERATIVE PROCESS PLAN  -  {part.name}")
    print("=" * 100)
    print(f"  Work material      : {part.material}")
    print(f"  Stock              : ø{part.stock_diameter} x {part.stock_length} mm bar")
    print(f"  Finished steps     : " +
          ", ".join(f"ø{s.diameter}x{s.length}" for s in part.steps))
    if part.thread_pitch:
        print(f"  Thread             : pitch {part.thread_pitch} mm over {part.thread_length} mm")
    if part.chamfer_size:
        print(f"  Chamfer            : {part.chamfer_size} mm x {part.chamfer_angle}°")
    print("-" * 100)
    print(f"{'#':>2} {'Operation':<34}{'Tool':<7}{'Vc':>5} {'N':>6} {'f':>6} {'ap':>5} {'x':>3} {'t,min':>7}")
    print("-" * 100)

    total = 0.0
    for op in ops:
        ap_s = f"{op.ap:.2f}" if op.ap is not None else "  - "
        print(f"{op.seq:>2} {op.name[:33]:<34}{op.tool_station:<7}"
              f"{op.Vc:>5.0f} {op.N:>6.0f} {op.feed:>6.3f} {ap_s:>5} "
              f"{op.passes:>3} {op.time_min:>7.3f}")
        total += op.time_min

    print("-" * 100)
    print(f"{'':>2} {'TOTAL CYCLE TIME (machining + approach)':<34}{'':<7}{'':>5} {'':>6} {'':>6} {'':>5} {'':>3} {total:>7.3f}")
    print(f"{'':>2} {'equivalent':<34} = {total*60:.1f} seconds per component")
    print("=" * 100)
    print("Tooling list")
    for st in sorted({o.tool_station: o.tool_desc for o in ops}.items()):
        print(f"   {st[0]} : {st[1]}")
    print("Operation notes")
    for op in ops:
        if op.note:
            print(f"   [{op.seq}] {op.note}")
    print()
    return total


# ----------------------------------------------------------------------------
# 6. TEST CASES
# ----------------------------------------------------------------------------

def test_case_1() -> PartSpec:
    """Stepped shaft with an M30x1.5 thread - mild steel."""
    return PartSpec(
        name="TEST CASE 1 - Stepped transmission shaft (MS)",
        material="MILD_STEEL", stock_diameter=50.0, stock_length=100.0,
        steps=[Step(30.0, 25.0), Step(40.0, 30.0), Step(50.0, 40.0)],
        facing_allowance=1.0, chamfer_size=2.0, chamfer_angle=45.0,
        thread_pitch=1.5, thread_length=20.0, thread_on_step=0,
        groove_width=4.0, groove_depth=2.0, max_spindle_rpm=3500.0)


def test_case_2() -> PartSpec:
    """Small aluminium pin, no thread - checks the no-thread/no-groove branch."""
    return PartSpec(
        name="TEST CASE 2 - Aluminium locating pin (no thread)",
        material="ALUMINIUM", stock_diameter=25.0, stock_length=60.0,
        steps=[Step(12.0, 20.0), Step(20.0, 25.0)],
        facing_allowance=0.8, chamfer_size=1.0, chamfer_angle=45.0,
        thread_pitch=0.0, thread_length=0.0,
        groove_width=0.0, groove_depth=0.0, max_spindle_rpm=6000.0)


def test_case_3() -> PartSpec:
    """Heavy stainless flange stub - large radial stock, coarse 2.5 mm thread."""
    return PartSpec(
        name="TEST CASE 3 - Stainless valve stem (heavy stock)",
        material="STAINLESS", stock_diameter=90.0, stock_length=150.0,
        steps=[Step(48.0, 40.0), Step(70.0, 45.0), Step(90.0, 50.0)],
        facing_allowance=1.5, chamfer_size=2.5, chamfer_angle=45.0,
        thread_pitch=2.5, thread_length=35.0, thread_on_step=0,
        groove_width=6.0, groove_depth=3.0, max_spindle_rpm=2500.0)


def main() -> None:
    print("\n" + "#" * 100)
    print("# TASK 3.1 - GENERATIVE CAPP FEATURE RECOGNIZER : TEST VERIFICATION RUN")
    print("#" * 100 + "\n")

    results = []
    for builder in (test_case_1, test_case_2, test_case_3):
        part = builder()
        ops = plan(part)
        total = print_plan(part, ops)
        results.append((part.name, len(ops), total))

        # --- automatic sanity checks (assertions act as the verification) ---
        assert ops[0].op_class == "FACE", "facing must be the first operation"
        assert ops[-1].op_class == "PART_OFF", "part-off must be the last operation"
        order = [PRECEDENCE[o.op_class] for o in ops]
        assert order == sorted(order), "operations are not in precedence order"
        assert all(o.N > 0 for o in ops), "a spindle speed came out non-positive"
        assert all(o.N <= part.max_spindle_rpm + 1e-6 for o in ops), "spindle limit exceeded"
        assert total > 0, "total time must be positive"
        if part.thread_pitch:
            th = [o for o in ops if o.op_class == "THREAD"][0]
            assert abs(th.feed - part.thread_pitch) < 1e-9, "threading feed must equal the pitch"
        print("   >>> SANITY CHECKS PASSED for this case\n")

    print("=" * 100)
    print("SUMMARY OF THE THREE TEST CASES")
    print("=" * 100)
    print(f"{'Case':<50}{'Ops':>6}{'Cycle time, min':>18}")
    for name, n, t in results:
        print(f"{name:<50}{n:>6}{t:>18.3f}")
    print("=" * 100)
    print("ALL TEST CASES COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
