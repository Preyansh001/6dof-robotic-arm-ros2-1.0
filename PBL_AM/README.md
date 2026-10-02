# PBL — Automation in Manufacturing

Solution to the three assignments in `PBL_AM_KPP.pdf`. **Submit the four PDFs in `PDF/`.**

| # | PDF | Pages | Covers the brief's deliverables |
|---|---|---|---|
| 1 | `PDF/Assignment1_FMC_Design_Document.pdf` | 13 | Machine specification sheet · feed drive and feedback sensor selection justification (with error budget) · AGV throughput calculations · cell layout diagram · collision-free simulation evidence · **App. A–C**: both G/M-code programs and the verification log |
| 2 | `PDF/Assignment2_Case_Study_Report.pdf` | 9 | Case study technical report (8 pp. + cover): CMM architecture, drives, probes, calibration and standards · non-contact evaluation · trade-off matrix · recommendation |
| 2 | `PDF/Assignment2_Seminar_Presentation.pdf` | 12 | Seminar presentation, 12 slides |
| 3 | `PDF/Assignment3_Code_and_Verification_Report.pdf` | 24 | Test verification report with ≥ 3 numerical test cases per task · **App. A–E**: all five commented source files |

Editable sources (`.docx`, `.pptx`) are kept beside each PDF so the blank
**Name / Enrolment / Class / Date** fields on the cover pages can be filled in and
the PDFs re-exported.

## Runnable files

```bash
cd Assignment3_Coding && for f in task3_*.py; do python3 "$f"; done   # all exit 0
cd Assignment1_FMC/simulation && python3 toolpath_simulator.py        # re-runs verification
```

Standard library only for Assignment 3; the simulator and the figure scripts use matplotlib.

## Notes

* The G-code simulator is written for this assignment. Its figures are its own output —
  **not** screenshots of CutViewer, LinuxCNC or FreeCAD. It performs real material removal
  (radius profile `r(z)` for turning, height map `z(x,y)` for milling), applies G41/G42
  compensation, and tests every rapid against the stock as it then stands. It is validated
  against two deliberately faulty programs, which it correctly rejects. It does not model
  holders, turret, fixture or kinematics, so it does not replace a single-block dry run.
* Assignment 2 cost figures are indicative ranges and the scrap rates illustrative — replace
  with plant data before use.
* Assignment 2 cites IS 2063 and IS 15250 as given in the brief; the technical content is
  anchored on ISO 10360 and ISO 230. Confirm current BIS part numbers before submission.
