#!/usr/bin/env python3
"""Proposed hybrid in-line / near-line inspection architecture."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

fig, ax = plt.subplots(figsize=(17.2, 9.0), dpi=150)
ax.set_xlim(-2, 114); ax.set_ylim(-18, 47); ax.axis("off")

E="#1f2d3d"; MACH="#dde6f1"; VIS="#e3eee1"; CMM="#f6e8ef"; DATA="#ece9f5"; BAD="#ffe3dc"

def box(x,y,w,h,t,fs=8.0,fill=MACH,bold=True,lw=1.5,r=0.9):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",
                 facecolor=fill,edgecolor=E,lw=lw,zorder=3))
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=fs,zorder=4,
            fontweight="bold" if bold else "normal",color="#10202f")
def lab(x,y,t,fs=7.8,ha="center",va="center",bold=False,color="#10202f",z=6):
    ax.text(x,y,t,ha=ha,va=va,fontsize=fs,zorder=z,
            fontweight="bold" if bold else "normal",color=color)
def arr(x1,y1,x2,y2,color=E,lw=1.8,ls="-",ms=15,z=5):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),zorder=z,
        arrowprops=dict(arrowstyle="-|>",color=color,lw=lw,ls=ls,
                        shrinkA=0,shrinkB=0,mutation_scale=ms))

lab(56,45.2,"Fig. A2.1  —  Proposed hybrid inspection architecture for the cylinder-block line",
    fs=13,bold=True)
lab(56,42.4,"100 % in-line non-contact gauging, with near-line DCC CMM sampling for full GD&T and gauge correlation",
    fs=9,color="#45535f")

# ---------------- production line -----------------------------------------
lab(2,37.4,"P R O D U C T I O N   L I N E      (takt 90 s)",fs=9.2,bold=True,ha="left",color="#2c3a47")
for t,x in (("OP 10\nRough mill\nfaces",2),("OP 20\nBore & hone\ncylinders",17),
            ("OP 30\nDrill & tap\noil galleries",32),("OP 40\nFinish mill\ndeck face",47)):
    box(x,26,12.5,8.4,t,fs=8.0)
for x in (14.5,29.5,44.5):
    arr(x,30.2,x+2.5,30.2)

# ---------------- in-line gauge -------------------------------------------
arr(59.5,30.2,64,30.2,lw=2.4)
box(64,23.6,27,13.2,"IN-LINE  GAUGING  STATION\n\n"
    "CCD / CMOS vision  +  3-D laser line scanner\n"
    "robot-presented, air-purged enclosure\n\n"
    "100 % of parts   ·   45 s  <  90 s takt",fs=8.2,fill=VIS)
lab(77.5,39.4,"CTQ set: bore Ø and position, deck flatness,\n"
              "drilling and thread presence, casting defects",fs=7.4,color="#3c5a3c")

arr(91,30.2,96.2,30.2,lw=2.4)
ax.add_patch(Circle((99.8,30.2),3.4,facecolor="#ffffff",edgecolor=E,lw=1.6,zorder=3))
lab(99.8,30.2,"PASS ?",fs=7.6,bold=True,z=4)
arr(99.8,33.6,99.8,37.6,lw=2.0)
box(92,37.6,15.6,5.2,"TO ASSEMBLY",fs=8.4,fill="#e8f3e8")
arr(99.8,26.8,99.8,21.4,color="#b03a2e",lw=2.0)
box(92,15.6,15.6,5.8,"REJECT /\nQUERY BAY",fs=8.0,fill=BAD)

# ---------------- near-line CMM -------------------------------------------
arr(77.5,23.6,77.5,17.6,color="#8e44ad",lw=2.0,ls=(0,(5,3)))
lab(79.2,20.6,"1 block in 17\n(SPC sample)",fs=7.4,ha="left",color="#8e44ad",bold=True)
box(57,4.8,34,12.8,"NEAR-LINE  DCC  COORDINATE  MEASURING  MACHINE\n\n"
    "moving bridge, granite table, CAA volumetric compensation\n"
    "continuous contact SCANNING probe + touch-trigger probe\n\n"
    "full GD&T scheme   ·   25 min per block\n"
    "acceptance to ISO 10360 / IS 15250",fs=8.0,fill=CMM)
lab(74,2.8,"climate-controlled room, 20 ± 1 °C, vibration-isolated base",fs=7.4,color="#6b4a62")

# ---------------- data / feedback -----------------------------------------
box(8,4.8,38,12.8,"S P C   /   M E S   D A T A   L A Y E R\n\n"
    "real-time control charts   ·   Cp / Cpk tracking\n"
    "automatic tool-offset feedback to OP 20 and OP 40\n"
    "gauge R & R correlation between vision and CMM",fs=8.0,fill=DATA)
arr(57,11.2,46.5,11.2,color="#5b4b8a",lw=2.0)
arr(64,24.6,46.5,16.6,color="#5b4b8a",lw=1.8,ls=(0,(5,3)))
lab(56.5,20.0,"100 % measurement\nstream",fs=7.3,color="#5b4b8a",bold=True)

ax.plot([27,27],[17.6,21.6],color="#b03a2e",lw=2.0,ls=(0,(5,3)),zorder=4)
ax.plot([27,23.2],[21.6,21.6],color="#b03a2e",lw=2.0,ls=(0,(5,3)),zorder=4)
arr(23.2,21.6,23.2,26.0,color="#b03a2e",lw=2.0,ls=(0,(5,3)))
lab(28.6,19.6,"closed-loop tool-offset correction",fs=7.6,ha="left",color="#b03a2e",bold=True)

# ---------------- rationale panel -----------------------------------------
box(2,-16.4,106,13.4,"",fill="#f7f9fc",lw=1.2,r=0.6)
lab(55,-5.4,"Why the hybrid, and not either technology on its own",fs=9.6,bold=True)
for i,txt in enumerate([
  "A full-GD&T CMM inspection takes 25 min against a 90 s takt — 17 machines would be needed for 100 % coverage, so a CMM alone can only ever sample.",
  "Non-contact gauging alone cannot reach blind bores, and cannot certify datum-referenced true position and cylindricity to a traceable standard.",
  "Together, vision catches every part and detects a process drift within one part, while the CMM certifies the measurement system and the full tolerance scheme."]):
    lab(5,-8.4-i*2.8,"•  "+txt,fs=8.2,ha="left")

plt.savefig("/home/user/6dof-robotic-arm-ros2-1.0/PBL_AM/Assignment2_Inspection/inspection_architecture.png",
            dpi=150,bbox_inches="tight",facecolor="white")
print("written")
