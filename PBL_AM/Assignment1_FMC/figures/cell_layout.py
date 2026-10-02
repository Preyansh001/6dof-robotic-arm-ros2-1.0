#!/usr/bin/env python3
"""Cell layout diagram for the Automated Flexible Manufacturing Cell."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle

fig, ax = plt.subplots(figsize=(17.5, 10.6), dpi=150)
ax.set_xlim(-6.2, 38.4); ax.set_ylim(-3.0, 20.8); ax.axis("off"); ax.set_aspect("equal")

E="#1f2d3d"; MACH="#d7e3f2"; STORE="#f8efd9"; INSP="#e3eee1"; WALK="#f2f3f5"
AGV="#c0392b"; ROBOT="#efe2f2"; FENCE="#8a97a6"

def box(x,y,w,h,t,fs=8.6,fill=MACH,bold=True,lw=1.5,ls="-"):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor=E,lw=lw,ls=ls,zorder=3))
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=fs,zorder=4,
            fontweight="bold" if bold else "normal",color="#10202f")
def lab(x,y,t,fs=7.6,ha="center",va="center",bold=False,color="#10202f",rot=0,z=6):
    ax.text(x,y,t,ha=ha,va=va,fontsize=fs,rotation=rot,zorder=z,
            fontweight="bold" if bold else "normal",color=color)
def arr(x1,y1,x2,y2,color=E,lw=1.3,ls="-",z=5,ms=12):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),zorder=z,
                arrowprops=dict(arrowstyle="->",color=color,lw=lw,ls=ls,
                                shrinkA=0,shrinkB=0,mutation_scale=ms))

ax.text(16.1,20.1,"Fig. A1.3  —  Layout of the Automated Flexible Manufacturing Cell (FMC)",
        ha="center",fontsize=13.5,fontweight="bold")
ax.text(16.1,19.2,"plan view  ·  cell envelope 32 m × 18 m  ·  all dimensions in metres",
        ha="center",fontsize=8.6,color="#45535f",style="italic")

# ---- safety fence -------------------------------------------------------
ax.add_patch(Rectangle((0,0),32.2,17.6,facecolor="none",edgecolor=FENCE,lw=2.4,
                       ls=(0,(7,3)),zorder=1))
lab(0.35,17.9,"perimeter guarding (2 m mesh fence)",fs=7.2,ha="left",color=FENCE)
box(28.9,-0.45,2.9,0.9,"INTERLOCKED\nGATE",fs=6.4,fill="#ffe9e4",lw=1.4)
box(0.6,-0.45,2.6,0.9,"LIGHT\nCURTAIN",fs=6.4,fill="#ffe9e4",lw=1.4)

# ---- maintenance strip --------------------------------------------------
ax.add_patch(Rectangle((1.0,15.75),30.0,0.85,facecolor="#f6f2e8",edgecolor="#b9ad93",
                       lw=1.0,ls=":",zorder=1))
lab(16.0,16.17,"M A I N T E N A N C E   /   S E R V I C E   Z O N E      (1.5 m clear behind every machine)",
    fs=7.4,color="#6d6450")

# ---- machines -----------------------------------------------------------
box(1.5,10.4,5.0,5.2,"RAW MATERIAL\nSTAGING\n\nbar stock Ø50–Ø90\n2-day buffer",fs=8.0,fill=STORE)
box(8.2,10.4,4.6,5.2,"TC-01\nCNC TURNING CENTRE\n2-axis (X, Z)\n\n12-station turret\nbar feeder + sub-spindle",fs=7.6)
box(14.3,10.4,4.6,5.2,"MC-01\n3-AXIS CNC VMC\n(X, Y, Z)\n\n24-pocket ATC\n4th-axis ready",fs=7.6)
box(20.4,10.4,3.6,5.2,"WASH  &\nDEBURR\n\nhigh-pressure\nwash, blow-off",fs=7.6,fill="#e2eef2")
box(25.5,10.4,5.4,5.2,"IN-LINE INSPECTION\n\nvision / laser gauge\n(100 % check)\n+ near-line DCC CMM\n(SPC sampling)",fs=7.4,fill=INSP)

# tool changer / turret swing clearance
for mx in (8.2, 14.3):
    ax.add_patch(Rectangle((mx-0.9,9.5),4.6+1.8,6.1,facecolor="none",
                           edgecolor="#c0392b",lw=1.1,ls=(0,(4,2.5)),zorder=2))
lab(21.6,9.75,"0.9 m tool-changer / turret\nswing clearance (dashed)",fs=6.6,
    ha="left",color="#c0392b")

# ---- robot on linear rail ----------------------------------------------
ax.add_patch(Rectangle((8.2,8.95),10.7,0.5,facecolor=ROBOT,edgecolor=E,lw=1.3,zorder=3))
lab(19.2,9.2,"7th-axis linear rail, 10.7 m",fs=6.8,ha="left",color="#6a4a73")
box(11.6,8.28,3.9,0.62,"6-AXIS LOAD / UNLOAD ROBOT",fs=6.4,fill=ROBOT,lw=1.4)

# ---- operator walkway ---------------------------------------------------
ax.add_patch(Rectangle((1.0,6.6),30.0,1.5,facecolor=WALK,edgecolor="#aab3bd",
                       lw=1.0,ls=":",zorder=1))
lab(16.0,7.35,"O P E R A T O R   W A L K W A Y   /   A C C E S S   A I S L E      (1.45 m clear)",
    fs=7.4,color="#6b7682")

# ---- AGV guide path -----------------------------------------------------
OUT_Y, RET_Y = 5.6, 1.5
ax.plot([1.6,30.6],[OUT_Y,OUT_Y],color=AGV,lw=3.0,solid_capstyle="round",zorder=2)
ax.plot([1.6,30.6],[RET_Y,RET_Y],color=AGV,lw=3.0,solid_capstyle="round",zorder=2)
ax.plot([1.6,1.6],[RET_Y,OUT_Y],color=AGV,lw=3.0,zorder=2)
ax.plot([30.6,30.6],[RET_Y,OUT_Y],color=AGV,lw=3.0,zorder=2)
for x in (7.0,13.0,19.0,25.0):
    arr(x,OUT_Y,x+1.6,OUT_Y,color=AGV,lw=2.2,ms=16)
for x in (25.0,19.0,13.0,7.0):
    arr(x+1.6,RET_Y,x,RET_Y,color=AGV,lw=2.2,ms=16)
lab(16.1,6.12,"AGV GUIDE PATH  —  outbound (loaded)",fs=7.6,bold=True,color=AGV)
lab(16.1,1.05,"AGV GUIDE PATH  —  return (empty)",fs=7.6,bold=True,color=AGV)

# P/D stations
for x,name in ((4.0,"P/D-1"),(10.5,"P/D-2"),(16.6,"P/D-3"),(22.2,"P/D-4"),(28.2,"P/D-5")):
    ax.plot([x,x],[OUT_Y,6.6],color=AGV,lw=2.0,ls=(0,(2,1.6)),zorder=2)
    ax.add_patch(Circle((x,OUT_Y),0.30,facecolor="#ffffff",edgecolor=AGV,lw=1.8,zorder=6))
    lab(x,OUT_Y-0.72,name,fs=6.6,bold=True,color=AGV)

# ---- finished goods -----------------------------------------------------
box(25.5,2.6,5.4,2.2,"FINISHED GOODS\n& DESPATCH BUFFER",fs=7.6,fill=STORE)
ax.plot([28.2,28.2],[RET_Y,2.6],color=AGV,lw=2.0,ls=(0,(2,1.6)),zorder=2)

# ---- ancillaries --------------------------------------------------------
box(1.5,2.6,3.2,2.2,"CELL\nCONTROLLER\n(MES / SCADA)",fs=7.0,fill="#ece9f5")
box(5.4,2.6,3.0,2.2,"CHIP & COOLANT\nMANAGEMENT",fs=7.0,fill="#eceff2")
box(9.2,2.6,3.0,2.2,"TOOL PRE-SET\n& CRIB",fs=7.0,fill="#eceff2")

# ---- route in / out of the cell ----------------------------------------
arr(-4.4,OUT_Y,1.6,OUT_Y,color=AGV,lw=2.4,ms=16)
lab(-5.9,OUT_Y,"from CENTRAL\nRAW STORE\n48 m",fs=7.0,ha="left",color=AGV,bold=True)
arr(30.6,RET_Y,36.4,RET_Y,color=AGV,lw=2.4,ms=16)
lab(36.7,RET_Y,"to DESPATCH\nDOCK\n64 m",fs=7.0,ha="left",color=AGV,bold=True)

# ---- process flow numbers ----------------------------------------------
flow=[(4.0,16.5,"1"),(10.5,16.5,"2"),(16.6,16.5,"3"),(22.2,16.5,"4"),(28.2,16.5,"5")]
for x,y,n in flow:
    ax.add_patch(Circle((x,y+0.55),0.42,facecolor="#1f4e79",edgecolor="white",lw=1.4,zorder=7))
    lab(x,y+0.55,n,fs=8.2,bold=True,color="white",z=8)
for (x1,_,_),(x2,_,_) in zip(flow[:-1],flow[1:]):
    arr(x1+0.55,17.05,x2-0.55,17.05,color="#1f4e79",lw=1.5,ms=13)

# ---- inter-station distances -------------------------------------------
ax.annotate("",xy=(10.5,0.45),xytext=(4.0,0.45),
            arrowprops=dict(arrowstyle="<->",color="#45535f",lw=1.0))
lab(7.25,0.62,"10 m",fs=6.8,color="#45535f")
ax.annotate("",xy=(16.6,0.45),xytext=(10.5,0.45),
            arrowprops=dict(arrowstyle="<->",color="#45535f",lw=1.0))
lab(13.55,0.62,"7 m",fs=6.8,color="#45535f")
ax.annotate("",xy=(22.2,0.45),xytext=(16.6,0.45),
            arrowprops=dict(arrowstyle="<->",color="#45535f",lw=1.0))
lab(19.4,0.62,"6 m",fs=6.8,color="#45535f")
ax.annotate("",xy=(28.2,0.45),xytext=(22.2,0.45),
            arrowprops=dict(arrowstyle="<->",color="#45535f",lw=1.0))
lab(25.2,0.62,"5 m",fs=6.8,color="#45535f")

# ---- legend -------------------------------------------------------------
lx,ly=-5.9,-1.55
items=[("machine / station",MACH),("storage & buffer",STORE),("inspection",INSP),
       ("robot handling",ROBOT),("walkway / maintenance",WALK)]
for i,(t,c) in enumerate(items):
    ax.add_patch(Rectangle((lx+i*6.3,ly),0.62,0.42,facecolor=c,edgecolor=E,lw=1.0))
    lab(lx+i*6.3+0.78,ly+0.21,t,fs=7.2,ha="left")
ax.plot([lx+32.0,lx+33.0],[ly+0.21,ly+0.21],color=AGV,lw=3.0)
lab(lx+33.2,ly+0.21,"AGV guide path",fs=7.2,ha="left")

lab(16.1,-2.55,"Material flow:  ① raw bar staging → ② CNC turning (TC-01) → ③ CNC milling (MC-01) "
    "→ ④ wash / deburr → ⑤ in-line inspection → finished goods.   "
    "Transfer between TC-01 and MC-01 is by the rail-mounted robot; all other moves are by AGV.",
    fs=7.6,color="#2c3a47")

plt.savefig("/home/user/6dof-robotic-arm-ros2-1.0/PBL_AM/Assignment1_FMC/figures/cell_layout.png",
            dpi=150,bbox_inches="tight",facecolor="white")
print("cell_layout.png written")
