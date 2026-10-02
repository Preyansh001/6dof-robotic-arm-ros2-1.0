# PBL — Automation in Manufacturing

Complete solution to the three Project-Based Learning assignments set in `PBL_AM_KPP.pdf`.

---

## Assignment 1 — Automated Flexible Manufacturing Cell (FMC)
*Complex Problem-Solving / Mini Project · CO-2, CO-3, CO-4 · SDG 9, SDG 12*

| Deliverable required by the brief | File |
|---|---|
| Technical Design Document | `Assignment1_FMC/Assignment1_Technical_Design_Document.docx` (13 pp.) |
| Code & Simulation Package — annotated executable G/M-code | `Assignment1_FMC/gcode/turning_shaft.nc`, `milling_plate.nc` |
| …with tool-path simulation proving collision-free verification | `Assignment1_FMC/simulation/toolpath_simulator.py`, `simulation_verification.log`, `turning_toolpath.png`, `milling_toolpath.png` |
| Cell Layout Diagram | `Assignment1_FMC/figures/cell_layout.png` (+ `cell_layout.py`) |

Covers machine-tool specification, the feed-drive and feedback selection that delivers
± 0.005 mm (with a full error budget), the two part programs, their verification, and
the AGV transport analysis.

```bash
cd Assignment1_FMC/simulation && python3 toolpath_simulator.py   # re-runs the verification
```

## Assignment 2 — CMM versus Non-Contact Vision Inspection
*Case Study & Seminar · CO-1, CO-5 · SDG 9, SDG 4*

| Deliverable required by the brief | File |
|---|---|
| Case Study Technical Report (6–8 pages) | `Assignment2_Inspection/Assignment2_Case_Study_Report.docx` (8 pp. + cover) |
| Seminar Presentation (10–12 slides) | `Assignment2_Inspection/Assignment2_Seminar_Presentation.pptx` (12 slides, with speaker notes) |
| Supporting figure | `Assignment2_Inspection/inspection_architecture.png` (+ `.py`) |

## Assignment 3 — CAPP & AS/RS Algorithms
*Coding / Simulation Micro-Project · CO-3, CO-4*

| Deliverable required by the brief | File |
|---|---|
| Code repository — fully commented source | `Assignment3_Coding/task3_1 … task3_5 (.py)` |
| Test Verification Report — ≥ 3 numerical test cases per task | `Assignment3_Coding/Assignment3_Test_Verification_Report.docx` (8 pp.) |
| Execution logs | `Assignment3_Coding/logs/*.log` |

| Task | Script |
|---|---|
| 3.1 Generative CAPP feature recognizer | `task3_1_capp_feature_recognizer.py` |
| 3.2 Tool offset & cutter radius compensation | `task3_2_tool_offset_compensation.py` |
| 3.3 AS/RS single- and dual-command cycle time | `task3_3_asrs_cycle_time.py` |
| 3.4 AGV fleet sizing model | `task3_4_agv_fleet_sizing.py` |
| 3.5 ADC barcode verification tool | `task3_5_barcode_verification.py` |

```bash
cd Assignment3_Coding
for f in task3_*.py; do python3 "$f"; done     # standard library only, no dependencies
```

All five scripts exit 0. Each asserts its own results, and three of the five include a
negative control (deliberately wrong inputs that must be rejected).

---

## Notes on verification

* The G-code simulator is **purpose-written for this assignment**. Its figures are its own
  output — they are **not** screenshots of CutViewer, LinuxCNC or FreeCAD. It models the tool
  as a cylinder and does not model holders, turret, fixture or machine kinematics, so it does
  not replace a single-block dry run on the machine.
* It performs real material removal (a radius profile `r(z)` for turning, a height map
  `z(x,y)` for milling) and tests every rapid traverse against the stock as it then stands.
  It applies G41/G42 cutter radius compensation. It is validated against two deliberately
  faulty programs, which it correctly rejects.
* Cost figures in Assignment 2 are **indicative ranges** to show relative scale, and the scrap
  rates in the economic model are illustrative. Replace both with plant data before use.
* Assignment 2 cites IS 2063 and IS 15250 as given in the brief; the technical content is
  anchored on ISO 10360 and ISO 230. Confirm current BIS part numbers before submission.
* The `.docx` cover pages have blank Name / Enrolment / Class / Date fields to fill in.
