---
title: "demo_340 — 2-D ideal valve with fibre-reinforced leaflets"
description: "demo_340: two anisotropic (FRH) leaflets in a pulsatile channel, with the fibre angle as the parameter and the archived AFSI displacement compared against Ryan et al. and Kamensky et al."
date: 2026-09-12
weight: 340
academic: true
---

## 1. What it is

Two thin leaflets sit in a straight channel driven by a pulsatile inlet profile;
they are fibre-reinforced hyperelastic (FRH) solids coupled to the fluid through
the immersed boundary. The demo has two axes: a comparison of the AFSI tip
displacement against published reference curves (Ryan et al. M2/M3, Kamensky et
al.), and a fibre-angle study at $45^\circ$, $60^\circ$ and $75^\circ$.

## 2. Configuration

<p class="tcaption">Table 1. Channel, leaflets and material. The fluid grid and the leaflet mesh are fixed; the fibre angle is the only parameter that changes between runs.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` (`main.py:39-40`) | $8.0 \times 1.61$ |
| Fluid cells | `Nx`, `Ny` | $128 \times 32$ (cell $0.0625 \times 0.0503$) |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Inlet profile | literal (`main.py:123`) | $5\,(\sin 2\pi t + 1.1)\,y\,(1.61 - y)$ |
| Outlet | — | $p = 0$ on the right edge |
| Leaflets | `lx`, `ly` | $0.0212 \times 0.7$, at $x \approx 1.9894$, $y = 0$ and $y = 0.91$ |
| Clamped edges | `dss(4)`, `dss(15)` | wall-attached edges, penalty `beta` $= 1\times10^{8}$ |
| Solid mesh size | Gmsh | $0.01$ |
| Material | `FRHMaterial` | `C0` $= 2\times10^{5}$, `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Fibre vectors | `f1_d`, `f1_u` | $45^\circ$: $(0.7071, \pm0.7071)$; $60^\circ$ and $75^\circ$ are commented out in `main.py` |
| Time step / end time | `dt`, `T` | $1/16000$ / $3.0$ ($48\,000$ steps) |
| Solver | `ChorinSolver` | $\mathrm{P2}$ velocity, $\mathrm{P1}$ pressure, force $\mathrm{P2}$ |

Environment overrides: `STEPS` only (it sets both the step count and
$T = \text{STEPS}\cdot\Delta t$; `STEPS=20` is the documented smoke test).

## 3. Files

| File | Role |
|---|---|
| `main.py` | Driver: fluid, FRH leaflets, penalty fixation, IB coupling, time loop |
| `materials.py` | `FRHMaterial` (used) and `NeoHookeanMaterial` (fallback, unused here) |
| `generate_mesh.py` | Gmsh leaflets → `plot/mesh-340.xdmf` (tag offsets $0$ and $10$) |
| `plot/plot_1.py` | AFSI against Ryan M2/M3 and Kamensky → `smoothed_x.png`, `smoothed_y.png` |
| `plot/plot_2.py` | Fibre-angle comparison → `Anisotropic_x_displacement.png`, `Anisotropic_y_displacement.png` |
| `plot/data/ani_{t,x,y}.csv` | Archived AFSI probe series ($302$ rows) for $45^\circ/60^\circ/75^\circ$ |
| `plot/{X_M2,X_FSI,x_dis_ALE,Y_FSI,y_M2,Y_ALE}.csv` | Digitised reference curves |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_340
python generate_mesh.py          # first run only
python main.py                   # full T = 3 s

cd plot && python plot_1.py      # comparison figure
python plot_2.py                 # fibre-angle figure
```

Switching the fibre angle means editing the active `f1_*` / material lines in
`main.py` (the $60^\circ$ and $75^\circ$ vectors are present but commented out).

## 5. Results and notes

The archived probe series ends at $t = 2.9999\,\mathrm{s}$:

<p class="tcaption">Table 2. Leaflet-tip displacement at the end of the run, against the published reference curves (all values in mesh units, endpoint of each series).</p>

| Source | $x$ displacement | $y$ displacement |
|---|---|---|
| AFSI, $45^\circ$ fibres | $0.5141$ | $0.2624$ |
| AFSI, $60^\circ$ fibres | $0.5099$ | $0.2587$ |
| AFSI, $75^\circ$ fibres | $0.4945$ | $0.2403$ |
| Ryan et al. M2 | $0.4614$ | $0.2083$ |
| Ryan et al. M3 | $0.4759$ | $0.2229$ |
| Kamensky et al. | $0.4753$ | $0.2228$ |

The angle trend is the expected one — the stiffer $75^\circ$ layup deflects least —
but all three AFSI runs sit above the reference band ($+8\,\%$ in $x$, up to
$+18\,\%$ in $y$ for $45^\circ$), which is worth keeping in mind when reading the
comparison figures.

Caveats:

* The generated figures are not archived, and the readme's own $60^\circ/75^\circ$
  provenance is only a comment: the CSV columns are named after AFSI run ids
  (`demo-340-000092/91/90`), not after angles.
* `main.py` hard-codes the facet-tag contract (`find(15)` upper, `find(4)` lower,
  `dxx(11)`/`dxx(1)`), so regenerating the mesh with a different tag offset
  silently misassigns the materials.
* Several config keys are never read (`Nl`, `E_s`, `nu_s`, `pressure_order`), and
  `beta` is described as a "root" penalty while `main.py` and the readme call the
  same thing the leaflet "tip".
* A commented-out block at the end of `main.py` refers to
  `data/ideal_middle_wall.txt`, which does not exist here — dead code from an
  earlier version.
* `main.py` calls SwanLab unconditionally, and `generate_mesh.py` never calls
  `gmsh.finalize()`.
