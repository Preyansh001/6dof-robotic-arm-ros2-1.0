#!/usr/bin/env python3
"""
Task 3.2 - CNC Tool Offset & Cutter Radius Compensation Calculator
=================================================================
Calculates the corrected tool-path coordinates for a given part profile when a
tool with a finite nose radius / cutter radius is used.

Two cases are handled with the same underlying geometry engine:

  TURNING  (X, Z plane)  - tool nose radius compensation (G41/G42 on a lathe).
                           The programmed point on a lathe is the *imaginary
                           tool nose*; the actual cutting point wanders around
                           the nose radius, which produces undercut on tapers
                           and arcs unless compensation is applied.

  MILLING  (X, Y plane)  - cutter radius compensation (G41 = cutter LEFT of the
                           programmed path, G42 = cutter RIGHT).

Geometry engine
---------------
The compensated path is the *offset* of the part profile by the tool radius,
taken on the side the tool body lies.  For a polyline this is computed by

  1. offsetting every straight segment perpendicular to itself by r, and
  2. intersecting each pair of neighbouring offset lines (a mitre joint).

Parallel neighbours (collinear segments) fall back to the plain perpendicular
offset, which is the correct limit of the mitre.

Run:  python3 task3_2_tool_offset_compensation.py
"""

from __future__ import annotations

import math
from typing import List, Tuple, Sequence

Pt = Tuple[float, float]

EPS = 1e-9


# ----------------------------------------------------------------------------
# 1. BASIC 2-D GEOMETRY
# ----------------------------------------------------------------------------

def _sub(a: Pt, b: Pt) -> Pt:
    return (a[0] - b[0], a[1] - b[1])


def _add(a: Pt, b: Pt) -> Pt:
    return (a[0] + b[0], a[1] + b[1])


def _scale(a: Pt, k: float) -> Pt:
    return (a[0] * k, a[1] * k)


def _norm(a: Pt) -> float:
    return math.hypot(a[0], a[1])


def _unit(a: Pt) -> Pt:
    n = _norm(a)
    if n < EPS:
        raise ValueError("zero-length segment in the profile")
    return (a[0] / n, a[1] / n)


def left_normal(d: Pt) -> Pt:
    """Unit normal 90 deg to the LEFT of direction d (d must be a unit vector)."""
    return (-d[1], d[0])


def right_normal(d: Pt) -> Pt:
    """Unit normal 90 deg to the RIGHT of direction d."""
    return (d[1], -d[0])


def line_intersection(p1: Pt, d1: Pt, p2: Pt, d2: Pt) -> Pt | None:
    """Intersection of line (p1 + t*d1) with line (p2 + s*d2); None if parallel."""
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None                      # parallel or collinear
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    t = (dx * d2[1] - dy * d2[0]) / den
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


def point_to_segment_distance(p: Pt, a: Pt, b: Pt) -> float:
    """Shortest distance from point p to the segment a-b."""
    ab = _sub(b, a)
    L2 = ab[0] ** 2 + ab[1] ** 2
    if L2 < EPS:
        return _norm(_sub(p, a))
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / L2))
    proj = (a[0] + t * ab[0], a[1] + t * ab[1])
    return _norm(_sub(p, proj))


def distance_to_polyline(p: Pt, poly: Sequence[Pt]) -> float:
    return min(point_to_segment_distance(p, poly[i], poly[i + 1])
               for i in range(len(poly) - 1))


# ----------------------------------------------------------------------------
# 2. THE OFFSET (COMPENSATION) ENGINE
# ----------------------------------------------------------------------------

def offset_polyline(pts: Sequence[Pt], r: float, side: str,
                    closed: bool = False) -> List[Pt]:
    """
    Offset an open or closed polyline by a distance r.

    side : 'left'  -> offset to the left of the direction of travel  (G41)
           'right' -> offset to the right of the direction of travel (G42)

    Returns the offset polyline with mitred corners.
    """
    if side not in ("left", "right"):
        raise ValueError("side must be 'left' or 'right'")
    if len(pts) < 2:
        raise ValueError("a profile needs at least two points")

    # Remove repeated points - a duplicated vertex would give a zero-length
    # segment with no defined direction.  This also tolerates a caller that
    # already closed the contour by repeating the first point at the end.
    clean: List[Pt] = [tuple(pts[0])]
    for p in pts[1:]:
        if _norm(_sub(p, clean[-1])) > 1e-9:
            clean.append(tuple(p))
    pts = clean
    if closed and _norm(_sub(pts[0], pts[-1])) > 1e-9:
        pts.append(pts[0])
    elif not closed and len(pts) < 2:
        raise ValueError("a profile needs at least two distinct points")

    nrm = left_normal if side == "left" else right_normal

    # one offset line per segment: (point on the line, direction)
    lines = []
    for i in range(len(pts) - 1):
        d = _unit(_sub(pts[i + 1], pts[i]))
        n = nrm(d)
        lines.append((_add(pts[i], _scale(n, r)), d, n))

    out: List[Pt] = []

    if not closed:
        out.append(lines[0][0])                      # start of the first offset line

    rng = range(len(lines)) if closed else range(1, len(lines))
    for i in rng:
        prev = lines[i - 1]
        cur = lines[i]
        ip = line_intersection(prev[0], prev[1], cur[0], cur[1])
        if ip is None:                               # collinear segments
            ip = _add(pts[i], _scale(cur[2], r))
        out.append(ip)

    if not closed:
        last_p, last_d, last_n = lines[-1]
        out.append(_add(pts[-1], _scale(last_n, r)))
    else:
        out.append(out[0])                           # close the contour

    return out


# ----------------------------------------------------------------------------
# 3. TURNING - TOOL NOSE RADIUS COMPENSATION
# ----------------------------------------------------------------------------

# Imaginary tool-nose direction for the usual Fanuc tip numbers, expressed as a
# unit vector (Z, X) pointing from the CENTRE of the nose radius towards the
# imaginary tip.  NOTE: the sign convention depends on whether the machine has a
# front or a rear tool post - always confirm against the control manual.
TIP_VECTORS = {
    0: (0.0, 0.0),                       # nose centre programmed directly
    9: (0.0, 0.0),
    1: (+0.70710678, +0.70710678),       # +Z, +X
    2: (-0.70710678, +0.70710678),       # -Z, +X
    3: (-0.70710678, -0.70710678),       # -Z, -X
    4: (+0.70710678, -0.70710678),       # +Z, -X
    5: (0.0, +1.0),                      # +X
    6: (-1.0, 0.0),                      # -Z
    7: (0.0, -1.0),                      # -X
    8: (+1.0, 0.0),                      # +Z
}


def turning_compensation(profile: Sequence[Pt], nose_radius: float,
                         tip_vector: Pt, material_side: str = "left"):
    """
    Compute the compensated path for a turned profile.

    profile       : list of (Z, X_radius) points describing the finished surface
    nose_radius   : R of the insert [mm]
    tip_vector    : unit vector (Z, X) from the nose centre to the imaginary tip
    material_side : which side of the direction of travel the MATERIAL lies on;
                    the tool is therefore offset to the opposite side

    Returns (centre_path, tip_path, max_uncompensated_error)
        centre_path - path of the CENTRE of the nose radius (true offset)
        tip_path    - where the imaginary tip must be commanded with G40
        error       - the largest deviation that would occur if the profile were
                      programmed directly on the tip with no compensation
    """
    tool_side = "right" if material_side == "left" else "left"
    centre_path = offset_polyline(profile, nose_radius, tool_side)

    # The imaginary tip sits at (centre + R * tip_vector).
    tip_path = [_add(c, _scale(tip_vector, nose_radius)) for c in centre_path]

    # If the operator ignored compensation he would drive the TIP along the
    # profile; the nose centre would then be at (profile - R*tip_vector) and the
    # surface actually produced is that centre path offset back by R.  The error
    # is the distance between the resulting surface and the wanted profile.
    err = 0.0
    for p in profile:
        wrong_centre = _sub(p, _scale(tip_vector, nose_radius))
        d = distance_to_polyline(wrong_centre, profile)
        err = max(err, abs(d - nose_radius))
    return centre_path, tip_path, err


# ----------------------------------------------------------------------------
# 4. MILLING - CUTTER RADIUS COMPENSATION
# ----------------------------------------------------------------------------

def milling_compensation(contour: Sequence[Pt], cutter_diameter: float,
                         gcode: str, closed: bool = True) -> List[Pt]:
    """
    Cutter radius compensation for a milled contour.

    gcode : 'G41' -> cutter kept to the LEFT  of the direction of travel
            'G42' -> cutter kept to the RIGHT of the direction of travel
    """
    gcode = gcode.upper()
    if gcode not in ("G41", "G42"):
        raise ValueError("gcode must be 'G41' or 'G42'")
    side = "left" if gcode == "G41" else "right"
    return offset_polyline(contour, cutter_diameter / 2.0, side, closed=closed)


def arc_to_polyline(centre: Pt, radius: float, start_deg: float,
                    end_deg: float, segments: int = 72) -> List[Pt]:
    """Chord the arc so that circular contours can use the same engine."""
    pts = []
    for i in range(segments + 1):
        a = math.radians(start_deg + (end_deg - start_deg) * i / segments)
        pts.append((centre[0] + radius * math.cos(a),
                    centre[1] + radius * math.sin(a)))
    return pts


# ----------------------------------------------------------------------------
# 5. REPORTING
# ----------------------------------------------------------------------------

def show(title: str, header: Tuple[str, str], original: Sequence[Pt],
         compensated: Sequence[Pt], limit: int = 12) -> None:
    print("-" * 78)
    print(title)
    print("-" * 78)
    a, b = header
    print(f"{'#':>3}  {'PROGRAMMED ' + a:>14}{'PROGRAMMED ' + b:>14}"
          f"{'  ':>4}{'COMPENSATED ' + a:>16}{'COMPENSATED ' + b:>16}")
    n = max(len(original), len(compensated))
    for i in range(min(n, limit)):
        o = original[i] if i < len(original) else ("", "")
        c = compensated[i] if i < len(compensated) else ("", "")
        os0 = f"{o[0]:14.4f}" if o[0] != "" else " " * 14
        os1 = f"{o[1]:14.4f}" if o[1] != "" else " " * 14
        cs0 = f"{c[0]:16.4f}" if c[0] != "" else " " * 16
        cs1 = f"{c[1]:16.4f}" if c[1] != "" else " " * 16
        print(f"{i:>3}  {os0}{os1}{'  ':>4}{cs0}{cs1}")
    if n > limit:
        print(f"      ... {n - limit} further points not shown")
    print()


# ----------------------------------------------------------------------------
# 6. TEST CASES
# ----------------------------------------------------------------------------

def test_case_1() -> None:
    """Turning: cylinder + 30 deg taper + cylinder, 0.8 mm nose radius."""
    print("=" * 78)
    print("TEST CASE 1 - TURNING, tool nose radius compensation")
    print("=" * 78)
    # profile in (Z, X_radius); cutting from the free end towards the chuck
    profile = [(0.0, 15.0), (-20.0, 15.0), (-40.0, 25.0), (-70.0, 25.0)]
    R = 0.8
    tip = TIP_VECTORS[3]                  # tip points -Z, -X (typical OD turning)

    centre, tip_path, err = turning_compensation(profile, R, tip, material_side="left")

    print(f"  Insert nose radius R      : {R} mm")
    print(f"  Imaginary tip vector (Z,X): ({tip[0]:+.4f}, {tip[1]:+.4f})  [Fanuc tip no. 3]")
    print(f"  Taper angle in the profile: {math.degrees(math.atan2(25-15, 20)):.2f} deg")
    show("Nose-centre path (what the control actually drives with G41/G42)",
         ("Z", "X"), profile, centre)
    show("Imaginary-tip path (what must be programmed if G40, i.e. no comp)",
         ("Z", "X"), profile, tip_path)
    print(f"  >>> Maximum profile error if compensation were OMITTED : {err:.4f} mm")
    print(f"      (this is the classic undercut on the tapered face)\n")

    # verification
    # The nose centre must never come CLOSER than R to the finished surface
    # (that would be a gouge); at convex mitre corners it is legitimately farther.
    for p in centre:
        d = distance_to_polyline(p, profile)
        assert d >= R - 1e-6, f"gouge: nose centre only {d:.4f} mm from the profile"
    assert err > 0.01, "a taper must produce a measurable uncompensated error"
    print("   >>> SANITY CHECKS PASSED\n")


def test_case_2() -> None:
    """Milling: rectangular pocket, inside contour, 10 mm cutter."""
    print("=" * 78)
    print("TEST CASE 2 - MILLING, rectangular pocket (G41, inside contour)")
    print("=" * 78)
    W, Hh = 60.0, 40.0
    contour = [(0.0, 0.0), (W, 0.0), (W, Hh), (0.0, Hh)]   # CCW, closed
    Dc = 10.0

    comp = milling_compensation(contour, Dc, "G41", closed=True)

    print(f"  Pocket size        : {W} x {Hh} mm")
    print(f"  Cutter diameter    : ø{Dc} mm  (radius {Dc/2} mm)")
    show("Cutter-centre path", ("X", "Y"), contour, comp)

    xs = [p[0] for p in comp[:-1]]
    ys = [p[1] for p in comp[:-1]]
    got_w, got_h = max(xs) - min(xs), max(ys) - min(ys)
    exp_w, exp_h = W - Dc, Hh - Dc
    print(f"  Cutter-centre rectangle : {got_w:.4f} x {got_h:.4f} mm")
    print(f"  Expected (W-D) x (H-D)  : {exp_w:.4f} x {exp_h:.4f} mm")
    assert abs(got_w - exp_w) < 1e-6 and abs(got_h - exp_h) < 1e-6, \
        "inside offset of a rectangle must shrink it by exactly one diameter"
    assert abs(min(xs) - Dc / 2) < 1e-6, "offset must start one radius in from the wall"
    print("   >>> SANITY CHECKS PASSED - offset is exactly one radius from every wall\n")


def test_case_3() -> None:
    """Milling: outside profile with G42, and a circular pocket."""
    print("=" * 78)
    print("TEST CASE 3 - MILLING, outside contour (G42) and circular pocket")
    print("=" * 78)
    contour = [(0.0, 0.0), (80.0, 0.0), (80.0, 50.0), (40.0, 70.0), (0.0, 50.0)]
    Dc = 12.0
    comp = milling_compensation(contour, Dc, "G42", closed=True)
    print(f"  Cutter diameter : ø{Dc} mm, outside contour, G42")
    show("Cutter-centre path around the outside of the part", ("X", "Y"), contour, comp)

    # every centre point must sit exactly one radius outside the part
    for p in comp[:-1]:
        d = distance_to_polyline(p, list(contour) + [contour[0]])
        assert d > Dc / 2 - 1e-6, f"cutter centre too close to the part: {d:.4f}"
    print("   >>> every cutter-centre point is at least one radius clear of the profile")

    # circular pocket
    Dpocket, Dcut = 40.0, 10.0
    circ = arc_to_polyline((0.0, 0.0), Dpocket / 2.0, 0.0, 360.0, segments=36)
    cc = milling_compensation(circ, Dcut, "G41", closed=True)
    radii = [math.hypot(p[0], p[1]) for p in cc[:-1]]
    print(f"\n  Circular pocket ø{Dpocket} mm with a ø{Dcut} mm cutter")
    print(f"  Cutter-centre radius : min {min(radii):.4f} / max {max(radii):.4f} mm")
    print(f"  Expected             : {(Dpocket - Dcut)/2:.4f} mm")
    assert abs(sum(radii)/len(radii) - (Dpocket - Dcut) / 2) < 0.05, \
        "circular pocket offset radius is wrong"
    print("   >>> SANITY CHECKS PASSED\n")


def main() -> None:
    print("\n" + "#" * 78)
    print("# TASK 3.2 - TOOL OFFSET / CUTTER RADIUS COMPENSATION : VERIFICATION RUN")
    print("#" * 78 + "\n")
    test_case_1()
    test_case_2()
    test_case_3()
    print("=" * 78)
    print("ALL THREE TEST CASES COMPLETED SUCCESSFULLY")
    print("=" * 78)


if __name__ == "__main__":
    main()
