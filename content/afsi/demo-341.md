---
title: "341: Sphere in a Driven Cubic Cavity"
description: "A sphere carried through a driven cubic cavity, in Navier–Stokes and immersed-boundary FSI."
date: 2026-09-12
weight: 341
academic: true
demo_id: demo_341
category: Application
dimension: 3D
solid_model: "elastic sphere, P = μ_s(F − F⁻ᵀ), μ_s = 0.1 (no volumetric term)"
coupling: "immersed boundary (`IBMesh3D` / `IBInterpolation3D`), serial only"
reference: "— (NS vs FSI cross-comparison on the same cavity)"
status: Partial
---

## 1. Introduction

A sphere is carried through a unit cubic cavity by the flow, first as a pure
Navier–Stokes run and then with the immersed-boundary coupling switched on. The
post-processing script samples the three centre lines at $t = 1\,\mathrm{s}$ and
compares NS against FSI across background grid densities — a minimal 3-D
counterpart to the 2-D lid-driven disc.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo341-setup.png" title="Figure 1. The cubic cavity and the immersed sphere." >}}

The cavity is the unit cube; the sphere of radius $0.2$ sits at
$(0.6, 0.5, 0.5)$ and spans a quarter of the cavity. The solid mesh is a Gmsh OCC
sphere with mesh size $0.01$.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the solid law, and the immersed-boundary coupling terms (see the symbol table page).{{< /color >}}

The solid carries the inline law
$\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$ with
`mu_s` $= 0.1$ and no volumetric term.

### 2.3 Boundary and initial conditions

The driving face is the lid at $y = 1$ with $u_x = 1$ (`marker_up`), every other
face is no-slip, and the pressure is pinned at the corner $(0,0,0)$. The cavity
starts from rest.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Physical parameters of the cubic-cavity case.</p>

| Quantity | Code name / env var | Value |
|---|---|---|
| Cavity | `Lx`, `Ly`, `Lz` | $1.0$, $1.0$, $1.0$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Driving | `UpVelocity` | $u_x = 1.0$ on the lid face ($y = 1$) |
| Pressure pin | — | $p = 0$ at the corner $(0,0,0)$ |
| Sphere centre / radius | `center`, `radius` | $(0.6, 0.5, 0.5)$ / $0.2$ |
| Solid mesh size | `mesh_size` | $0.01$ (Gmsh OCC sphere, not exposed as a parameter) |
| Solid law | inline | $\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$, `mu_s` $= 0.1$ (no volumetric term) |

{{< color "red" >}}TODO: dimensionless numbers and the sphere-to-cavity mass and stiffness ratios if the case is to be reported dimensionless.{{< /color >}}

## 3. Numerical setup

<p class="tcaption">Table 2. Numerical setup.</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid cells | `Nx`, `Ny`, `Nz` ← `GRID` | `GRID`$^3$, default $32^3$ ($8^3$, $16^3$, $32^3$ in the readme) |
| Velocity / force / pressure spaces | `*_order` | $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ |
| Time step | `dt` | $1/200$ |
| Default end time / steps | `T`, `num_steps` | $10.0$ s / $2000$; `STEPS` overrides both |

The readme's headline case is $\mathrm{GRID} = 16$ with `STEPS` $= 200$, i.e.
$t = 1\,\mathrm{s}$; running without `STEPS` gives a $2000$-step run instead. The
drivers are **serial only** — like the 2-D IBM demos, the marker map is not
MPI-safe.

Environment overrides: `GRID` (background grid), `STEPS` (step count, which
resets $T = \text{STEPS}\cdot\Delta t$), `CASE` (output subdirectory name).

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the three centre-line profiles at $t = 1\,\mathrm{s}$
with and without the sphere (the demo's own NS vs FSI comparison), the sphere's
centroid travel and maximum nodal displacement, the fluid energy and pressure
norms $u_{L2}$ / $p_{L2}$, and the residual out-of-plane velocity on the $z$-line.

### 4.2 Comparison with reference

{{< figure src="/afsi/demo341-results.png" title="Figure 2. The demo's own post-processing at $GRID = 8$ after 20 steps: the three centrelines with and without the sphere." >}}

{{< color "red" >}}TODO: comparison against a body-fitted reference solution on the same cavity — no reference values are archived, so NS/FSI agreement is the only comparison available so far.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Centreline $u_x$ (through sphere) |  |  |  |
| Centreline peak deficit |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid comparison across $8^3 / 16^3 / 32^3$ — the live run used $GRID = 16$ only; no refinement study exists.{{< /color >}}

### 4.4 Flow and deformation fields

A live run ($GRID = 16$, 200 steps, $t = 1$ s) was made as shipped except for two
environment overrides added here (`OUTPUT_PATH`, `MESH_341`) and a copy of the
driver with the SwanLab calls replaced by a CSV logger.

{{< figure src="/afsi/demo341-3d-scene.png" title="Figure 3. The $t = 1$ s state, rendered with PyVista. Top left: the cavity boundary coloured by speed — the lid at $y = 1$ carries $|u| = 1$, the four side walls the return flow and the floor none. Top right: the octant mesh and the immersed sphere, which spans a quarter of the cavity. Bottom left: streamlines seeded on a disc just upstream of the sphere; they wrap round its shoulder and rejoin the primary vortex. Bottom right: the tetrahedral sphere coloured by nodal displacement." >}}

{{< figure src="/afsi/demo341-trajectory.png" title="Figure 4. The sphere over the run. It starts at $(0.6, 0.5, 0.5)$ and drifts to $(0.528, 0.492, 0.500)$ — 0.073 m, or 0.37 radii — while its nodes move up to $0.107$, more than half a radius, so the sphere is being carried and deformed rather than simply translated. The drift is in $-x$, opposite the lid motion, which is the return branch of the primary vortex." >}}

{{< figure src="/afsi/demo341-centerlines.png" title="Figure 5. The three centreline profiles at $t = 1$ s, in the form `plot/plot_lines.py` extracts them. The shaded band is the sphere's span; markers inside it are the nodes the immersed boundary overwrites, which is why they must be excluded before comparing with a body-fitted reference." >}}

<p class="tcaption">Table 3. The live run.</p>

| Quantity | Value |
|---|---|
| Steps / wall time | $200$ steps at $GRID = 16$, $479\,\mathrm{s}$ serial |
| $u_{L2}$ | $0 \to 0.0411$, still growing at $t = 1$ s (the cavity takes several seconds to reach its steady state) |
| $p_{L2}$ | settles at $5.6\times10^{-3}$ after $t \approx 0.4$ s |
| Boundary speeds | lid mean $0.78$ (perturbed near the sphere), floor $1.6\times10^{-18}$ |
| Sphere | centroid travel $0.073$, $\max\lvert u_s\rvert = 0.107$ against a radius of $0.2$ |
| $u_z$ on the $z$-line | $\le 2.5\times10^{-3}$ — the flow stays essentially two-component in the mid-planes |

Two notes on reading these. The case is a **lid-driven cavity**, not an inlet
problem: the driver is internally consistent (the moving lid is `marker_up`
$= y = 1$ with $u_x = 1$, every other face no-slip), so the readme's "inlet"
wording is the mislabel, and no run is needed to resolve it. And the sphere
reaches only $t = 1$ s of the $10$ s the readme suggests, so the wake is still
developing — Figure 5 is the $t = 1$ s state that `plot_lines.py` is written for.

## 5. Discussion and limitations

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
* No run outputs are archived: the directory holds only the five source files,
  and `*.xdmf`/`*.h5` are git-ignored by design, so the mesh, the fields and the
  `line_*.csv`/`line_*.png` comparisons all have to be regenerated.

## 6. Reproducibility

<p class="tcaption">Table 4. Files in the demo.</p>

| File | Role |
|---|---|
| `generate_mesh.py` | Gmsh sphere mesh → `plot/mesh-341.xdmf` |
| `navier-stokes.py` | Pure NS run on the same cavity → `plot/ns_N<grid>/velocity.xdmf` |
| `fsi_paralell.py` | FSI run with `IBMesh3D`/`IBInterpolation3D` → `plot/fsi_N<grid>/` |
| `plot/plot_lines.py` | Samples $(x,0.5,0.5)$, $(0.5,y,0.5)$, $(0.5,0.5,z)$ at $t = 1\,\mathrm{s}$ (nearest stored frame), writes `line_{x,y,z}.csv/.png` |
| `readme.md` | Structure, run commands, environment table, post-processing, performance note |

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_341

python generate_mesh.py                      # solid mesh first

GRID=16 STEPS=200 python navier-stokes.py    # NS,  t = 1 s
GRID=16 STEPS=200 python fsi_paralell.py     # FSI, t = 1 s

cd plot && python plot_lines.py              # line_*.csv / line_*.png
```

Cost on this machine (serial):

| Grid | cells | per step | source |
|---|---|---|---|
| $8^3$ | $512$ | $1.1\,\mathrm{s}$ | measured |
| $16^3$ | $4096$ | $2.8\,\mathrm{s}$ | measured |
| $32^3$ | $32768$ | $\approx 12\,\mathrm{s}$ | readme (extrapolates as $\approx N^{5}$: $N^3$ for the fluid solve times $N^2$ markers in the IBM loop) |

So the $200$-step run to $t = 1$ s at $GRID = 16$ takes $479\,\mathrm{s}$; the same run
at $GRID = 32$ would take about $40$ minutes, and the readme's default $T = 10$ s
(2000 steps) would be $6.7$ hours at $GRID = 16$ and $\approx 27$ hours at $GRID = 32$.

## References

{{< color "red" >}}TODO: references — none cited yet; add a 3-D lid-driven-cavity reference if the mid-plane profiles are compared against one.{{< /color >}}
