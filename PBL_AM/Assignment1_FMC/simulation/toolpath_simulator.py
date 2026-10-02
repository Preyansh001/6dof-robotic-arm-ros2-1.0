#!/usr/bin/env python3
"""
G/M-code Tool Path Simulator and Collision Verifier
===================================================
Purpose-written verification tool for the Assignment 1 part programs.  It
interprets the G-code, removes material from a model of the stock and reports
any rapid traverse that would strike remaining material, together with a set of
programming-practice checks.  It then plots the verified tool path.

What it does
------------
  * tokenises the G-code and expands
        - subprogram calls            M98 P.... L..  / M99
        - lathe one-shot cycles       G90 (turning), G92 (threading), G94 (facing)
        - milling canned cycles       G81 / G83 peck drilling, G80 cancel
        - circular interpolation      G02 / G03 with I, J
  * runs a MATERIAL REMOVAL model
        - turning : a 2-D radius profile r(z) over the length of the bar
        - milling : a 2.5-D height map z(x, y) over the plate
    and flags any G00 move whose tool body passes through material that has not
    yet been cut - i.e. a genuine collision check, not merely a drawing.
  * checks programming practice: spindle running before cutting, feed rate set,
    tool length compensation active, cutter compensation cancelled before a tool
    change, travel inside the machine envelope.
  * writes a PNG of the verified tool path.

Limitations (stated honestly)
-----------------------------
This is a geometric verifier written for this assignment.  It models the tool as
a cylinder of the declared diameter and does not model the tool holder, the
turret, the fixture or machine kinematics.  It is not a substitute for a final
dry run on the machine, and the plots it produces are its own output - they are
not screenshots of CutViewer, LinuxCNC or FreeCAD.

Run:  python3 toolpath_simulator.py
"""

from __future__ import annotations

import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GCODE_DIR = os.path.join(HERE, "..", "gcode")

# ----------------------------------------------------------------------------
# 1. TOKENISER
# ----------------------------------------------------------------------------

_COMMENT = re.compile(r"\([^)]*\)")
_WORD = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")


def strip_block(line: str) -> str:
    """Remove comments, the % tape marks and anything after a ';'."""
    line = _COMMENT.sub(" ", line)
    line = line.split(";")[0]
    return line.replace("%", " ").strip().upper()


def parse_block(line: str) -> Dict[str, float]:
    """Return {letter: value} for one block.  Repeated G words are kept in 'G*'."""
    words: Dict[str, float] = {}
    gs: List[float] = []
    for letter, value in _WORD.findall(strip_block(line)):
        v = float(value)
        if letter == "G":
            gs.append(v)
        elif letter == "M":
            words.setdefault("M*", [])  # type: ignore[arg-type]
            words["M*"].append(v)       # type: ignore[index]
        else:
            words[letter] = v
    if gs:
        words["G*"] = gs                # type: ignore[assignment]
    return words


def load_programs(path: str) -> Tuple[List[str], Dict[int, List[str]]]:
    """Split a file into the main program and any subprograms keyed by O number."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.readlines()

    programs: Dict[int, List[str]] = {}
    order: List[int] = []
    current: Optional[int] = None
    for line in raw:
        s = strip_block(line)
        m = re.match(r"^O(\d+)", s)
        if m:
            current = int(m.group(1))
            programs[current] = []
            order.append(current)
            continue
        if current is not None and s:
            programs[current].append(line)
    if not order:
        raise ValueError(f"no O-number program found in {path}")
    main = programs[order[0]]
    subs = {n: programs[n] for n in order[1:]}
    return main, subs


def _offset_polyline(pts, r, side):
    """
    Offset a polyline by r to the 'left' or 'right' of the direction of travel.
    Straight segments are offset perpendicular to themselves and neighbouring
    offset lines are intersected (mitre joint).  This is the geometry a control
    performs internally for G41 / G42 cutter radius compensation.
    """
    clean = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-9:
            clean.append(p)
    if len(clean) < 2:
        return list(pts)

    lines = []
    for i in range(len(clean) - 1):
        dx = clean[i + 1][0] - clean[i][0]
        dy = clean[i + 1][1] - clean[i][1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        nx, ny = (-uy, ux) if side == "left" else (uy, -ux)
        lines.append(((clean[i][0] + r * nx, clean[i][1] + r * ny), (ux, uy), (nx, ny)))

    out = [(lines[0][0][0], lines[0][0][1], clean[0][2])]
    for i in range(1, len(lines)):
        (p1, d1, _), (p2, d2, n2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-12:                      # collinear - plain offset
            ip = (clean[i][0] + r * n2[0], clean[i][1] + r * n2[1])
        else:
            ddx, ddy = p2[0] - p1[0], p2[1] - p1[1]
            t = (ddx * d2[1] - ddy * d2[0]) / den
            ip = (p1[0] + t * d1[0], p1[1] + t * d1[1])
        out.append((ip[0], ip[1], clean[i][2]))
    lp, _, ln = lines[-1]
    out.append((clean[-1][0] + r * ln[0], clean[-1][1] + r * ln[1], clean[-1][2]))
    return out


# ----------------------------------------------------------------------------
# 2. MOVE RECORD
# ----------------------------------------------------------------------------

@dataclass
class Move:
    kind: str                 # 'rapid' | 'feed' | 'thread' | 'dwell'
    start: Tuple[float, float, float]
    end: Tuple[float, float, float]
    tool: str = ""
    tool_dia: float = 0.0
    feed: float = 0.0
    block: str = ""
    line_no: int = 0


@dataclass
class Issue:
    severity: str             # 'ERROR' | 'WARNING' | 'INFO'
    line_no: int
    block: str
    message: str


# ----------------------------------------------------------------------------
# 3. INTERPRETER
# ----------------------------------------------------------------------------

class Interpreter:
    """Executes the subset of G-code used by the Assignment 1 programs."""

    ARC_SEGMENTS = 72

    def __init__(self, machine: str, tool_table: Dict[str, float],
                 envelope: Dict[str, Tuple[float, float]]):
        if machine not in ("lathe", "mill"):
            raise ValueError("machine must be 'lathe' or 'mill'")
        self.machine = machine
        self.tool_table = tool_table          # {'T0101': diameter_or_width}
        self.envelope = envelope
        self.moves: List[Move] = []
        self.issues: List[Issue] = []

        # Modal state.  The tool starts at the MACHINE REFERENCE POINT, not at
        # the part datum - starting it at (0,0,0) would place it inside the bar.
        if machine == "lathe":
            self.pos = [envelope["X"][1], 0.0, envelope["Z"][1]]
        else:
            self.pos = [0.0, 0.0, envelope["Z"][1]]
        self.motion = 0
        self.feed = 0.0
        self.spindle_on = False
        self.tlo_active = False               # G43
        self.cutter_comp = 0                  # 0 / 41 / 42
        self.absolute = True                  # mill G90/G91
        self.tool = ""
        self.canned: Optional[dict] = None    # active drilling cycle
        self.lathe_cycle: Optional[dict] = None
        self.comp_buffer: Optional[List[Tuple[float, float, float]]] = None
        self.retract_plane = "G99"
        self.initial_z = 0.0

    # -- helpers ------------------------------------------------------------
    def _issue(self, sev: str, line_no: int, block: str, msg: str) -> None:
        self.issues.append(Issue(sev, line_no, block, msg))

    def _tool_dia(self) -> float:
        return self.tool_table.get(self.tool, 0.0)

    def _emit(self, kind: str, end: Tuple[float, float, float],
              block: str, line_no: int) -> None:
        # While G41/G42 is active the programmed points describe the PART
        # contour, not the cutter centre.  They are collected here and offset
        # by the tool radius when G40 cancels compensation.
        if (self.machine == "mill" and self.cutter_comp and kind == "feed"):
            if self.comp_buffer is None:
                self.comp_buffer = [tuple(self.pos)]      # type: ignore[list-item]
                self._comp_meta = (block, line_no)
            self.comp_buffer.append(end)
            self.pos = list(end)
            return
        start = tuple(self.pos)                      # type: ignore[assignment]
        self.moves.append(Move(kind, start, end, self.tool, self._tool_dia(),
                               self.feed, block, line_no))
        self.pos = list(end)

    def _flush_comp(self) -> None:
        """Offset the buffered contour by the tool radius and emit the real path."""
        if not self.comp_buffer or len(self.comp_buffer) < 2:
            self.comp_buffer = None
            return
        side = "left" if self.cutter_comp == 41 else "right"
        r = self._tool_dia() / 2.0
        # buffer[0] is where the tool stood when G41/G42 was commanded; the
        # remaining points are the PART CONTOUR.  A real control performs
        # "start-up" compensation: during the lead-in block it drives to the
        # point offset PERPENDICULAR to the start of the first contour element,
        # rather than mitring the lead-in into the contour (which would gouge
        # the finished wall).  Only the contour is therefore offset here.
        lead_from = self.comp_buffer[0]
        contour = self.comp_buffer[1:]
        if len(contour) < 2:
            self.comp_buffer = None
            return
        path = [lead_from] + _offset_polyline(contour, r, side)
        block, line_no = getattr(self, "_comp_meta", ("", 0))
        self.pos = list(path[0])
        for pt in path[1:]:
            start = tuple(self.pos)
            self.moves.append(Move("feed", start, tuple(pt), self.tool,
                                   self._tool_dia(), self.feed,
                                   block + "  [G4x compensated]", line_no))
            self.pos = list(pt)
        # The cutter is physically left at the last COMPENSATED point.  The G40
        # block then retracts from there, exactly as a real control does -
        # restoring the programmed contour point instead would drag the cutter
        # across the finished wall one radius oversize.
        self.comp_buffer = None

    # -- the main loop ------------------------------------------------------
    def run(self, main: List[str], subs: Dict[int, List[str]]) -> None:
        self._execute(main, subs, depth=0)

    def _execute(self, lines: List[str], subs: Dict[int, List[str]], depth: int) -> None:
        if depth > 8:
            raise RuntimeError("subprogram nesting too deep - possible recursion")

        for raw in lines:
            block = strip_block(raw)
            if not block:
                continue
            line_no = 0
            mN = re.search(r"\bN(\d+)", block)
            if mN:
                line_no = int(mN.group(1))
            w = parse_block(raw)
            gs: List[float] = w.get("G*", [])        # type: ignore[assignment]
            ms: List[float] = w.get("M*", [])        # type: ignore[assignment]

            # ---- M codes -------------------------------------------------
            for mcode in ms:
                if mcode in (3, 4):
                    self.spindle_on = True
                elif mcode == 5:
                    self.spindle_on = False
                elif mcode == 6:
                    self._flush_comp()
                    if self.cutter_comp:
                        self._issue("ERROR", line_no, block,
                                    "tool change with cutter compensation still active")
                    self.tlo_active = False
                elif mcode == 98:
                    p = int(w.get("P", 0))
                    reps = int(w.get("L", 1))
                    if p not in subs:
                        self._issue("ERROR", line_no, block, f"subprogram O{p:04d} not found")
                    else:
                        for _ in range(max(1, reps)):
                            self._execute(subs[p], subs, depth + 1)
                elif mcode == 99:
                    return
                elif mcode == 30:
                    if self.cutter_comp:
                        self._issue("ERROR", line_no, block,
                                    "program ended with cutter compensation active")

            if "T" in w:
                t = int(w["T"])
                self.tool = f"T{t:04d}" if self.machine == "lathe" else f"T{t:02d}"
            if "F" in w:
                self.feed = w["F"]
            if "S" in w:
                pass

            # ---- G codes that change state --------------------------------
            for g in gs:
                if g == 43:
                    self.tlo_active = True
                elif g == 49:
                    self.tlo_active = False
                elif g in (41, 42):
                    self.cutter_comp = int(g)
                elif g == 40:
                    self._flush_comp()        # emit the compensated contour first
                    self.cutter_comp = 0
                elif g == 80:
                    self.canned = None
                elif g in (98, 99):
                    self.retract_plane = f"G{int(g)}"
                elif self.machine == "mill" and g == 90:
                    self.absolute = True
                elif self.machine == "mill" and g == 91:
                    self.absolute = False

            # ---- G28 reference return -------------------------------------
            if 28 in gs:
                tgt = list(self.pos)
                if self.machine == "mill":
                    tgt[2] = self.envelope["Z"][1]
                else:
                    tgt[0], tgt[2] = self.envelope["X"][1], self.envelope["Z"][1]
                self._emit("rapid", tuple(tgt), block, line_no)  # type: ignore[arg-type]
                self.lathe_cycle = None
                continue

            # ---- G04 dwell ------------------------------------------------
            if 4 in gs:
                self.moves.append(Move("dwell", tuple(self.pos), tuple(self.pos),  # type: ignore[arg-type]
                                       self.tool, self._tool_dia(), 0.0, block, line_no))
                continue

            # ---- lathe one-shot cycles ------------------------------------
            if self.machine == "lathe":
                cyc = next((g for g in gs if g in (90, 92, 94)), None)
                if cyc is not None:
                    self.lathe_cycle = {"type": int(cyc)}
                if self.lathe_cycle and ("X" in w or "Z" in w) and not (
                        set(gs) & {0, 1, 2, 3, 28}):
                    self._lathe_cycle(w, block, line_no)
                    continue
                if set(gs) & {0, 1, 2, 3}:
                    self.lathe_cycle = None

            # ---- milling canned cycles ------------------------------------
            if self.machine == "mill":
                cyc = next((g for g in gs if g in (81, 83)), None)
                if cyc is not None:
                    self.initial_z = self.pos[2]
                    self.canned = {"type": int(cyc), "Z": w.get("Z", 0.0),
                                   "R": w.get("R", 0.0), "Q": w.get("Q", 0.0)}
                    self._drill(w, block, line_no)
                    continue
                if self.canned and ("X" in w or "Y" in w) and not (set(gs) & {0, 1, 2, 3, 28, 80}):
                    self._drill(w, block, line_no)
                    continue

            # ---- ordinary motion -------------------------------------------
            motion = next((g for g in gs if g in (0, 1, 2, 3)), None)
            if motion is not None:
                self.motion = int(motion)
            has_axis = any(k in w for k in ("X", "Y", "Z", "I", "J", "U", "W"))
            if not has_axis:
                continue

            target = self._target(w)

            if self.motion in (2, 3):
                self._arc(target, w, block, line_no)
            elif self.motion == 0:
                self._emit("rapid", target, block, line_no)
            else:
                if self.feed <= 0:
                    self._issue("ERROR", line_no, block, "cutting move with no feed rate set")
                if not self.spindle_on:
                    self._issue("ERROR", line_no, block, "cutting move with the spindle stopped")
                self._emit("feed", target, block, line_no)

            self._check_envelope(line_no, block)

    # -- target resolution --------------------------------------------------
    def _target(self, w: Dict[str, float]) -> Tuple[float, float, float]:
        x, y, z = self.pos
        if self.machine == "mill":
            if self.absolute:
                x = w.get("X", x); y = w.get("Y", y); z = w.get("Z", z)
            else:
                x += w.get("X", 0.0); y += w.get("Y", 0.0); z += w.get("Z", 0.0)
        else:
            x = w.get("X", x)
            z = w.get("Z", z)
            if "U" in w:
                x += w["U"]
            if "W" in w:
                z += w["W"]
        return (x, y, z)

    # -- arcs ---------------------------------------------------------------
    def _arc(self, target, w, block, line_no) -> None:
        sx, sy, sz = self.pos
        i, j = w.get("I", 0.0), w.get("J", 0.0)
        cx, cy = sx + i, sy + j
        r0 = math.hypot(sx - cx, sy - cy)
        r1 = math.hypot(target[0] - cx, target[1] - cy)
        if abs(r0 - r1) > 0.01:
            self._issue("ERROR", line_no, block,
                        f"arc end point is not on the arc: start R={r0:.3f}, end R={r1:.3f}")
        a0 = math.atan2(sy - cy, sx - cx)
        a1 = math.atan2(target[1] - cy, target[0] - cx)
        ccw = self.motion == 3
        if abs(a1 - a0) < 1e-9:
            sweep = 2 * math.pi if ccw else -2 * math.pi      # full circle
        else:
            sweep = (a1 - a0) % (2 * math.pi) if ccw else -((a0 - a1) % (2 * math.pi))
        for k in range(1, self.ARC_SEGMENTS + 1):
            a = a0 + sweep * k / self.ARC_SEGMENTS
            pt = (cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                  sz + (target[2] - sz) * k / self.ARC_SEGMENTS)
            self._emit("feed", pt, block, line_no)

    # -- drilling canned cycles --------------------------------------------
    def _drill(self, w, block, line_no) -> None:
        x = w.get("X", self.pos[0]); y = w.get("Y", self.pos[1])
        c = self.canned
        assert c is not None
        self._emit("rapid", (x, y, max(self.pos[2], c["R"])), block, line_no)
        self._emit("rapid", (x, y, c["R"]), block, line_no)
        if c["type"] == 83 and c["Q"] > 0:
            z = c["R"]
            while z > c["Z"] + 1e-9:
                z = max(c["Z"], z - c["Q"])
                self._emit("feed", (x, y, z), block, line_no)
                if z > c["Z"] + 1e-9:
                    self._emit("rapid", (x, y, c["R"]), block, line_no)
                    self._emit("rapid", (x, y, z + 1.0), block, line_no)
        else:
            self._emit("feed", (x, y, c["Z"]), block, line_no)
        back = c["R"] if self.retract_plane == "G99" else self.initial_z
        self._emit("rapid", (x, y, back), block, line_no)

    # -- lathe one-shot cycles ---------------------------------------------
    def _lathe_cycle(self, w, block, line_no) -> None:
        c = self.lathe_cycle
        assert c is not None
        xs, _, zs = self.pos
        xt = w.get("X", xs)
        zt = w.get("Z", c.get("Z", zs))
        c["Z"] = zt
        kind = "thread" if c["type"] == 92 else "feed"

        if c["type"] == 94:                       # end facing cycle
            self._emit("rapid", (xs, 0.0, zt), block, line_no)
            self._emit("feed",  (xt, 0.0, zt), block, line_no)
            self._emit("rapid", (xs, 0.0, zt), block, line_no)
            self._emit("rapid", (xs, 0.0, zs), block, line_no)
        else:                                     # G90 turning / G92 threading
            self._emit("rapid", (xt, 0.0, zs), block, line_no)
            self._emit(kind,    (xt, 0.0, zt), block, line_no)
            self._emit("rapid", (xs, 0.0, zt), block, line_no)
            self._emit("rapid", (xs, 0.0, zs), block, line_no)

    # -- envelope -----------------------------------------------------------
    def _check_envelope(self, line_no: int, block: str) -> None:
        for axis, idx in (("X", 0), ("Y", 1), ("Z", 2)):
            if axis not in self.envelope:
                continue
            lo, hi = self.envelope[axis]
            v = self.pos[idx]
            if v < lo - 1e-6 or v > hi + 1e-6:
                self._issue("ERROR", line_no, block,
                            f"{axis}={v:.3f} is outside the machine travel [{lo}, {hi}]")


# ----------------------------------------------------------------------------
# 4. MATERIAL REMOVAL + COLLISION CHECK - TURNING
# ----------------------------------------------------------------------------

def verify_turning(moves: List[Move], stock_dia: float, stock_len: float,
                   face_z: float = 2.0, dz: float = 0.25) -> List[Issue]:
    """
    Two-dimensional turning simulation.

    The bar is modelled as a radius profile r(z).  Every cutting move lowers the
    profile; every rapid traverse is then tested against the profile as it stands
    at that moment, so a rapid that would hit uncut material is reported.
    """
    issues: List[Issue] = []
    n = int(stock_len / dz) + 1
    zs = np.linspace(-stock_len, 0.0, n)
    radius = np.full(n, stock_dia / 2.0)
    CLEAR = 0.05                      # mm of permitted approach clearance

    def idx(z: float) -> Optional[int]:
        if z < -stock_len or z > 0.0:
            return None
        return int(round((z + stock_len) / dz))

    for mv in moves:
        x0, _, z0 = mv.start
        x1, _, z1 = mv.end
        r0, r1 = x0 / 2.0, x1 / 2.0
        steps = max(2, int(max(abs(z1 - z0), abs(r1 - r0)) / dz) + 1)

        for k in range(steps + 1):
            t = k / steps
            z = z0 + (z1 - z0) * t
            r = r0 + (r1 - r0) * t
            i = idx(z)
            if i is None:
                continue
            if mv.kind in ("feed", "thread"):
                if r < radius[i]:
                    radius[i] = max(r, 0.0)       # cut
            else:                                  # rapid
                # Nothing can be struck where no material remains (the bar has
                # been faced or parted right through at this Z station).
                if radius[i] <= 1e-6:
                    continue
                if r < radius[i] - CLEAR:
                    issues.append(Issue(
                        "ERROR", mv.line_no, mv.block,
                        f"RAPID into material: at Z={z:.2f} the tool is at radius "
                        f"{r:.2f} mm but material remains to radius {radius[i]:.2f} mm"))
                    break
    return issues


# ----------------------------------------------------------------------------
# 5. MATERIAL REMOVAL + COLLISION CHECK - MILLING
# ----------------------------------------------------------------------------

def verify_milling(moves: List[Move], x_range, y_range, top_z: float,
                   grid: float = 1.0) -> Tuple[List[Issue], np.ndarray, tuple]:
    """
    Two-and-a-half dimensional milling simulation on a height map z(x, y).

    Cutting moves stamp the tool disc down to the commanded Z; rapid moves are
    tested against the height map as it stands, so a rapid that would plough
    through uncut stock is reported.
    """
    issues: List[Issue] = []
    nx = int((x_range[1] - x_range[0]) / grid) + 1
    ny = int((y_range[1] - y_range[0]) / grid) + 1
    hmap = np.full((ny, nx), top_z, dtype=float)
    gx = np.linspace(x_range[0], x_range[1], nx)
    gy = np.linspace(y_range[0], y_range[1], ny)
    GX, GY = np.meshgrid(gx, gy)
    CLEAR = 0.05

    for mv in moves:
        if mv.kind == "dwell":
            continue
        r = max(mv.tool_dia / 2.0, 0.01)
        x0, y0, z0 = mv.start
        x1, y1, z1 = mv.end
        dist = math.dist((x0, y0, z0), (x1, y1, z1))
        steps = max(1, int(dist / max(grid, 0.5)))

        for k in range(steps + 1):
            t = k / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            z = z0 + (z1 - z0) * t
            disc = (GX - x) ** 2 + (GY - y) ** 2 <= r * r
            if not disc.any():
                continue
            if mv.kind == "feed":
                np.minimum(hmap, np.where(disc, z, hmap), out=hmap)
            else:
                hit = disc & (hmap > z + CLEAR)
                if hit.any():
                    worst = float(hmap[hit].max())
                    issues.append(Issue(
                        "ERROR", mv.line_no, mv.block,
                        f"RAPID into material at X{x:.1f} Y{y:.1f} Z{z:.2f}: "
                        f"stock still stands at Z={worst:.2f}"))
                    break
    return issues, hmap, (gx, gy)


# ----------------------------------------------------------------------------
# 6. PLOTTING
# ----------------------------------------------------------------------------

def plot_turning(moves: List[Move], out: str, stock_dia: float, stock_len: float) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=150)
    ax.add_patch(plt.Rectangle((-stock_len, 0.0), stock_len, stock_dia / 2.0,
                               facecolor="#e8e2d4", edgecolor="#9a8f77",
                               lw=1.2, zorder=0, label="bar stock (half section)"))
    profile_z = [0, 0, -2, -25, -25, -55, -55, -100]
    profile_x = [0, 13, 15, 15, 20, 20, 25, 25]
    ax.plot(profile_z, profile_x, color="#1f6f3f", lw=2.4, zorder=5,
            label="finished profile")

    first = {"rapid": True, "feed": True, "thread": True}
    for mv in moves:
        if mv.kind == "dwell":
            continue
        z = [mv.start[2], mv.end[2]]
        x = [mv.start[0] / 2.0, mv.end[0] / 2.0]
        if mv.kind == "rapid":
            ax.plot(z, x, color="#c0392b", lw=0.7, ls=(0, (4, 3)), zorder=3,
                    label="rapid (G00)" if first["rapid"] else None)
            first["rapid"] = False
        elif mv.kind == "thread":
            ax.plot(z, x, color="#8e44ad", lw=1.8, zorder=4,
                    label="threading (G92)" if first["thread"] else None)
            first["thread"] = False
        else:
            ax.plot(z, x, color="#1b4f8a", lw=1.2, zorder=4,
                    label="cutting feed" if first["feed"] else None)
            first["feed"] = False

    ax.set_xlabel("Z  [mm]"); ax.set_ylabel("X radius  [mm]")
    ax.set_title("Fig. A1.1 - Verified tool path, O0001 stepped transmission shaft "
                 "(turning, half section)", fontweight="bold", fontsize=11)
    ax.set_xlim(-110, 15); ax.set_ylim(-3, 32)
    ax.grid(alpha=0.3, ls=":"); ax.legend(loc="upper left", fontsize=8, framealpha=0.95)
    ax.axhline(0, color="#444", lw=1.0, ls="-.")
    ax.text(-105, 0.8, "spindle centre line", fontsize=7, color="#444")
    fig.tight_layout(); fig.savefig(out, facecolor="white"); plt.close(fig)


def plot_milling(moves: List[Move], hmap: np.ndarray, grid: tuple, out: str) -> None:
    gx, gy = grid
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(13, 10.4), dpi=150,
                                  gridspec_kw={"height_ratios": [1.55, 1]})

    ax.add_patch(plt.Rectangle((-80, -50), 160, 100, facecolor="#eef1f4",
                               edgecolor="#8a97a6", lw=1.4, zorder=0, label="plate 160 x 100"))
    ax.add_patch(plt.Rectangle((-70, -20), 60, 40, facecolor="none",
                               edgecolor="#1f6f3f", lw=2.0, ls="--", zorder=5,
                               label="finished pocket geometry"))
    ax.add_patch(plt.Circle((45, 0), 20, facecolor="none", edgecolor="#1f6f3f",
                            lw=2.0, ls="--", zorder=5))
    for hx, hy in ((65, 35), (-65, 35), (-65, -35), (65, -35)):
        ax.add_patch(plt.Circle((hx, hy), 4, facecolor="none", edgecolor="#1f6f3f",
                                lw=2.0, ls="--", zorder=5))

    first = {"rapid": True, "feed": True}
    for mv in moves:
        if mv.kind == "dwell":
            continue
        xs = [mv.start[0], mv.end[0]]; ys = [mv.start[1], mv.end[1]]
        if mv.kind == "rapid":
            ax.plot(xs, ys, color="#c0392b", lw=0.6, ls=(0, (4, 3)), zorder=3,
                    label="rapid (G00)" if first["rapid"] else None)
            first["rapid"] = False
        else:
            ax.plot(xs, ys, color="#1b4f8a", lw=0.9, zorder=4,
                    label="cutting feed" if first["feed"] else None)
            first["feed"] = False

    ax.set_aspect("equal"); ax.set_xlim(-135, 135); ax.set_ylim(-62, 62)
    ax.set_xlabel("X  [mm]"); ax.set_ylabel("Y  [mm]")
    ax.set_title("Fig. A1.2 - Verified tool path, O0002 cover plate (plan view)",
                 fontweight="bold", fontsize=11)
    ax.grid(alpha=0.3, ls=":"); ax.legend(loc="upper right", fontsize=8, ncol=2, framealpha=0.95)

    im = ax2.pcolormesh(gx, gy, hmap, cmap="viridis", shading="auto")
    ax2.set_xlim(-135, 135); ax2.set_ylim(-62, 62)
    ax2.set_aspect("equal"); ax2.set_xlabel("X  [mm]"); ax2.set_ylabel("Y  [mm]")
    ax2.set_title("Simulated material removal - final height map z(x, y) of the machined plate",
                  fontweight="bold", fontsize=10)
    cb = fig.colorbar(im, ax=ax2, fraction=0.025, pad=0.02)
    cb.set_label("Z  [mm]", fontsize=8)

    fig.tight_layout(); fig.savefig(out, facecolor="white"); plt.close(fig)


# ----------------------------------------------------------------------------
# 7. DRIVER
# ----------------------------------------------------------------------------

def report(title: str, interp: Interpreter, extra: List[Issue]) -> int:
    print("=" * 86)
    print(title)
    print("=" * 86)
    print(f"  Blocks interpreted into {len(interp.moves)} elementary moves")
    kinds = {}
    for m in interp.moves:
        kinds[m.kind] = kinds.get(m.kind, 0) + 1
    print("  Move breakdown : " + ", ".join(f"{k} = {v}" for k, v in sorted(kinds.items())))
    tools = sorted({m.tool for m in interp.moves if m.tool})
    print(f"  Tools used     : {', '.join(tools)}")
    zs = [m.end[2] for m in interp.moves]
    print(f"  Z range swept  : {min(zs):.2f} to {max(zs):.2f} mm")

    issues = interp.issues + extra
    errors = [i for i in issues if i.severity == "ERROR"]
    warns = [i for i in issues if i.severity == "WARNING"]
    print("-" * 86)
    if not issues:
        print("  VERIFICATION RESULT :  PASS")
        print("  No collisions, no envelope violations and no programming-practice")
        print("  errors were detected.  The tool path is collision free.")
    else:
        for i in issues[:25]:
            print(f"  [{i.severity:<7}] N{i.line_no:<5} {i.message}")
            print(f"              block: {i.block[:70]}")
        if len(issues) > 25:
            print(f"  ... and {len(issues) - 25} further messages")
        print("-" * 86)
        print(f"  VERIFICATION RESULT :  {'FAIL' if errors else 'PASS WITH WARNINGS'}"
              f"   ({len(errors)} errors, {len(warns)} warnings)")
    print("=" * 86 + "\n")
    return len(errors)


def main() -> int:
    print("\n" + "#" * 86)
    print("# ASSIGNMENT 1 - G/M-CODE TOOL PATH SIMULATION AND COLLISION VERIFICATION")
    print("#" * 86 + "\n")

    total_errors = 0

    # ---------------- turning -------------------------------------------
    lathe_tools = {"T0101": 0.0, "T0202": 0.0, "T0303": 3.0, "T0404": 0.0}
    it = Interpreter("lathe", lathe_tools,
                     {"X": (-5.0, 300.0), "Z": (-120.0, 300.0)})
    main_p, subs = load_programs(os.path.join(GCODE_DIR, "turning_shaft.nc"))
    it.run(main_p, subs)
    extra = verify_turning(it.moves, stock_dia=50.0, stock_len=100.0)
    total_errors += report("PROGRAM O0001 - turning_shaft.nc  (stepped transmission shaft)",
                           it, extra)
    plot_turning(it.moves, os.path.join(HERE, "turning_toolpath.png"), 50.0, 100.0)
    print(f"  tool path plot written to simulation/turning_toolpath.png\n")

    # ---------------- milling -------------------------------------------
    mill_tools = {"T01": 63.0, "T02": 12.0, "T03": 10.0, "T04": 8.0}
    im = Interpreter("mill", mill_tools,
                     {"X": (-400.0, 400.0), "Y": (-250.0, 250.0), "Z": (-250.0, 60.0)})
    main_p, subs = load_programs(os.path.join(GCODE_DIR, "milling_plate.nc"))
    im.run(main_p, subs)
    extra, hmap, grid = verify_milling(im.moves, (-80, 80), (-50, 50), top_z=0.0)
    total_errors += report("PROGRAM O0002 - milling_plate.nc  (cover plate)", im, extra)
    plot_milling(im.moves, hmap, grid, os.path.join(HERE, "milling_toolpath.png"))
    print(f"  tool path plot written to simulation/milling_toolpath.png\n")

    # ---------------- NEGATIVE CONTROL -----------------------------------
    # A verifier that can only ever report PASS proves nothing.  Two programs
    # containing KNOWN faults are run to demonstrate that the checker detects
    # them.  Both are expected to FAIL.
    print("=" * 86)
    print("NEGATIVE CONTROL - deliberately faulty programs that MUST be rejected")
    print("=" * 86)

    bad_lathe = """O9001 (DELIBERATELY FAULTY - RAPIDS STRAIGHT INTO THE BAR)
N10 G21 G40 G97 G99
N20 T0101
N30 G97 S800 M03
N40 G00 X52.0 Z2.0
N50 G00 X10.0 Z-30.0   (RAPID THROUGH THE UNCUT DIA 50 BAR)
N60 G01 Z-40.0 F0.2
N70 M30
"""
    path = os.path.join(HERE, "_negative_control_lathe.nc")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(bad_lathe)
    it2 = Interpreter("lathe", lathe_tools, {"X": (-5.0, 300.0), "Z": (-120.0, 300.0)})
    m2, s2 = load_programs(path)
    it2.run(m2, s2)
    bad_issues = verify_turning(it2.moves, stock_dia=50.0, stock_len=100.0)
    n_bad = len([i for i in bad_issues if i.severity == "ERROR"])
    print(f"  Faulty lathe program  : {n_bad} collision(s) detected", end="")
    print("  -> CHECKER WORKING" if n_bad else "  -> CHECKER FAILED TO DETECT")
    for i in bad_issues[:2]:
        print(f"      N{i.line_no}: {i.message}")
    assert n_bad > 0, "the collision checker failed to detect a deliberate crash"

    bad_mill = """O9002 (DELIBERATELY FAULTY - NO SPINDLE, NO FEED, RAPID INTO STOCK)
N10 G21 G17 G40 G80 G90
N20 T02 M06
N30 G90 G54 G00 X-40.0 Y0.0
N40 G43 H02 Z50.0
N50 G00 Z-5.0            (RAPID PLUNGE INTO SOLID STOCK)
N60 G01 X0.0 Y0.0        (CUTTING WITH THE SPINDLE STOPPED AND NO FEED)
N70 M30
"""
    path2 = os.path.join(HERE, "_negative_control_mill.nc")
    with open(path2, "w", encoding="utf-8") as fh:
        fh.write(bad_mill)
    im2 = Interpreter("mill", mill_tools,
                      {"X": (-400.0, 400.0), "Y": (-250.0, 250.0), "Z": (-250.0, 60.0)})
    m3, s3 = load_programs(path2)
    im2.run(m3, s3)
    bad2, _, _ = verify_milling(im2.moves, (-80, 80), (-50, 50), top_z=0.0)
    allbad = im2.issues + bad2
    n_bad2 = len([i for i in allbad if i.severity == "ERROR"])
    print(f"  Faulty mill program   : {n_bad2} fault(s) detected", end="")
    print("  -> CHECKER WORKING" if n_bad2 else "  -> CHECKER FAILED TO DETECT")
    for i in allbad[:3]:
        print(f"      N{i.line_no}: {i.message}")
    assert n_bad2 > 0, "the mill checker failed to detect deliberate faults"
    os.remove(path); os.remove(path2)
    print("  >>> the verifier correctly rejects known-bad programs, so the PASS")
    print("      results reported above for O0001 and O0002 are meaningful.")
    print("=" * 86 + "\n")

    # ---------------- dimensional check of the simulated plate -----------
    gx, gy = grid
    def depth_at(x, y):
        return float(hmap[int(np.argmin(abs(gy - y))), int(np.argmin(abs(gx - x)))])
    print("=" * 86)
    print("DIMENSIONAL CHECK OF THE SIMULATED PLATE")
    print("=" * 86)
    # Floor depths, and - crucially - points just INSIDE and just OUTSIDE each
    # pocket wall.  These wall checks are what prove that G41/G42 cutter radius
    # compensation has been applied: without it the pockets come out one cutter
    # radius oversize and the "just outside" points would read -6 instead of -0.5.
    checks = [("rectangular pocket floor",     (-40.0, 0.0),   -6.0, 0.25),
              ("circular pocket floor",        (45.0, 0.0),    -6.0, 0.25),
              ("faced top surface",            (0.0, 0.0),     -0.5, 0.25),
              ("uncut corner of the plate",    (-78.0, -48.0), -0.5, 0.6),
              ("rect pocket, 2 mm INSIDE +X wall",  (-12.0, 0.0),  -6.0, 0.25),
              ("rect pocket, 2 mm OUTSIDE +X wall", (-8.0, 0.0),   -0.5, 0.25),
              ("rect pocket, 2 mm INSIDE +Y wall",  (-40.0, 18.0), -6.0, 0.25),
              ("rect pocket, 2 mm OUTSIDE +Y wall", (-40.0, 22.0), -0.5, 0.25),
              ("circ pocket, R18 (inside wall)",    (63.0, 0.0),   -6.0, 0.25),
              ("circ pocket, R22 (outside wall)",   (67.0, 0.0),   -0.5, 0.25),
              ("rect pocket, 2 mm OUTSIDE -Y wall", (-55.0, -22.0), -0.5, 0.25)]
    ok = True
    for name, (x, y), expect, tol in checks:
        got = depth_at(x, y)
        good = abs(got - expect) <= tol
        ok &= good
        print(f"  {name:<28} at X{x:>7.1f} Y{y:>6.1f} : Z = {got:>7.2f}  "
              f"(expected {expect:+.2f} +/- {tol})  {'OK' if good else 'OUT OF TOLERANCE'}")
    print("=" * 86)
    print(f"\nOVERALL: {'ALL PROGRAMS VERIFIED COLLISION FREE' if total_errors == 0 else 'ERRORS FOUND - SEE ABOVE'}")
    return 0 if (total_errors == 0 and ok) else 1


if __name__ == "__main__":
    sys.exit(main())
