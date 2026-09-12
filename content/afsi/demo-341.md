---
title: "demo_341 — sphere in a driven cubic cavity (3-D)"
description: "demo_341: a Gmsh sphere carried through a unit cubic cavity, run both as pure Navier–Stokes and as immersed-boundary FSI, with a mid-line comparison at t = 1 s."
date: 2026-09-12
weight: 341
academic: true
---

## 1. What it is

A sphere is carried through a unit cubic cavity by the flow, first as a pure
Navier–Stokes run and then with the immersed-boundary coupling switched on. The
post-processing script samples the three centre lines at $t = 1\,\mathrm{s}$ and
compares NS against FSI across background grid densities — a minimal 3-D
counterpart to the 2-D lid-driven disc.

## 2. Configuration

<p class="tcaption">Table 1. Parameters of the cubic-cavity case.</p>

| Quantity | Code name / env var | Value |
|---|---|---|
| Cavity | `Lx`, `Ly`, `Lz` | $1.0$, $1.0$, $1.0$ |
| Fluid cells | `Nx`, `Ny`, `Nz` ← `GRID` | `GRID`$^3$, default $32^3$ ($8^3$, $16^3$, $32^3$ in the readme) |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Driving | `UpVelocity` | $u_x = 1.0$ on the marked inlet face |
| Pressure pin | — | $p = 0$ at the corner $(0,0,0)$ |
| Sphere centre / radius | `center`, `radius` | $(0.6, 0.5, 0.5)$ / $0.2$ |
| Solid mesh size | `mesh_size` | $0.01$ (Gmsh OCC sphere, not exposed as a parameter) |
| Solid law | inline | $\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$, `mu_s` $= 0.1$ (no volumetric term) |
| Velocity / force / pressure spaces | `*_order` | $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ |
| Time step | `dt` | $1/200$ |
| Default end time / steps | `T`, `num_steps` | $10.0$ s / $2000$; `STEPS` overrides both |

The readme's headline case is $\mathrm{GRID} = 16$ with `STEPS` $= 200$, i.e.
$t = 1\,\mathrm{s}$; running without `STEPS` gives a $2000$-step run instead.

Environment overrides: `GRID` (background grid), `STEPS` (step count, which
resets $T = \text{STEPS}\cdot\Delta t$), `CASE` (output subdirectory name).

## 3. Files

| File | Role |
|---|---|
| `generate_mesh.py` | Gmsh sphere mesh → `plot/mesh-341.xdmf` |
| `navier-stokes.py` | Pure NS run on the same cavity → `plot/ns_N<grid>/velocity.xdmf` |
| `fsi_paralell.py` | FSI run with `IBMesh3D`/`IBInterpolation3D` → `plot/fsi_N<grid>/` |
| `plot/plot_lines.py` | Samples $(x,0.5,0.5)$, $(0.5,y,0.5)$, $(0.5,0.5,z)$ at $t = 1\,\mathrm{s}$ (nearest stored frame), writes `line_{x,y,z}.csv/.png` |
| `readme.md` | Structure, run commands, environment table, post-processing, performance note |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_341

python generate_mesh.py                      # solid mesh first

GRID=16 STEPS=200 python navier-stokes.py    # NS,  t = 1 s
GRID=16 STEPS=200 python fsi_paralell.py     # FSI, t = 1 s

cd plot && python plot_lines.py              # line_*.csv / line_*.png
```

## 5. Results and notes

**No run outputs are archived** for this demo: the directory holds only the five
source files, and `*.xdmf`/`*.h5` are git-ignored by design, so the mesh, the
fields and the `line_*.csv`/`line_*.png` comparisons all have to be regenerated.
The only numbers recorded in the sources are the single-core cost quoted in the
readme — about $1.4\,\mathrm{s}$ per step on $16^3$ and $12\,\mathrm{s}$ per step
on $32^3$ — and the recommended grids $8^3/16^3/32^3$.

Caveats:

* The inlet Dirichlet condition for $u_x = 1$ is attached to the facet marker for
  the $y = 1$ face, not to the $x = 0$ face the readme calls the inlet, while
  $x = 0$ receives the no-slip condition. Which face actually carries the inflow
  is unclear from the sources.
* `plot/plot_lines.py` reads `velocity.xdmf` together with the matching
  `velocity.h5` (raw `h5py`, key `Function/f`) and assumes the $\mathrm{P1}$
  output space, so it only works with these two drivers' output.
* `generate_mesh.py` must run before either driver: `fsi_paralell.py` reads
  `plot/mesh-341.xdmf` with no existence check.
* The drivers call SwanLab; the readme notes that the network calls are simply
  blocked offline and do not affect the solve.
* `lambda_s = 10` is defined but unused — the sphere carries no volumetric term,
  so it is effectively incompressibility-free.
