---
title: "demo_400 — 2-D turtle under a periodic follower pressure"
description: "demo_400: an immersed turtle outline with fixed head and tail, a per-step follower pressure along the spine, and limbs that flap with the flow."
date: 2026-09-12
weight: 400
academic: true
---

## 1. What it is

An immersed turtle outline — a narrow head and tail plus four limb lobes — sits in
a straight channel. The head and tail facets are held by a penalty, the limbs are
advected by the surrounding flow, and a periodic **follower pressure** is applied
along the spine direction. It is the demo that exercises tag-driven fixation,
traction that follows the deformed geometry, and a selectable pressure waveform.

## 2. Configuration

<p class="tcaption">Table 1. Parameters (`configuration.py` and `main.py`). Units are CGS, as in the source.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx`, `Ly` | $200.0 \times 100.0$ |
| Fluid cells | `Nx`, `Ny` | $128 \times 64$ quadrilaterals (cell $1.5625^{2}$) |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Solid outline | `turtle_solid.geo` | $40$ points, characteristic length $0.01$; shifted then scaled $\times100$ |
| Solid law | inline | $\mathbf{P}_{\text{iso}} = \mu_s J^{-1}(\mathbf{F} - \tfrac{I_1}{2}\mathbf{F}^{-\mathrm{T}})$, $\mathbf{P}_{\text{vol}} = \lambda_s \ln J\,\mathbf{F}^{-\mathrm{T}}$ |
| Solid parameters | `mu_s`, `lambda_s` | $1\times10^{4}$ each ($\nu_s = 0.45$ is stored but unused) |
| Fixation | `beta`, tag $15$ | $1\times10^{6}$ penalty on the head/tail facets |
| Follower pressure | `p_amp`, `p_period` | $100.0$ over a period of $2.0\,\mathrm{s}$ |
| Waveform | `waveform`, `fast_ratio` | `fast_open` with a fast-phase fraction of $0.1$ |
| Traction facets | `dss(16)`, `dss(17)` | limb edges; the direction is the tag-16→tag-17 centroid vector, updated every step |
| Time step / end time | `dt`, `T` | $5\times10^{-5}$ / $30.0$ ($600\,000$ steps) |
| Output cadence | `TimeManager(fps=20)` | every $1000$ steps ($0.05\,\mathrm{s}$) |

There are **no environment overrides**; the module has no `os.environ` lookup at
all, and its `nssolver` key is decorative — `ChorinSolver` is instantiated
directly.

## 3. Files

| File | Role |
|---|---|
| `configuration.py` | All parameters, derived step count, output/experiment naming |
| `generate_mesh.py` | Gmsh mesh of `turtle_solid.geo` → `turtle_mesh.xdmf` (with cell/facet tags) |
| `main.py` | Driver: fluid, IB coupling, follower pressure, penalty fixation, XDMF output |
| `turtle_solid.geo` | The solid outline that is actually meshed (spine lines $16/17$, head–tail line $15$) |
| `turtle.geo` | A pygmsh-generated variant that also contains a fluid box; **not** referenced by the generator |
| `readme.md` | Chinese documentation of geometry, coupling, run command and outputs |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_400
python generate_mesh.py     # produces turtle_mesh.xdmf next to main.py
python main.py              # or: mpirun -n <N> python main.py
```

## 5. Results and notes

**No results are archived**: the directory has no `.xdmf`, `.h5`, `.csv`, `.json`
or image output, and none of the `~/afsi-data/demo-400/...` directories exist.
The numbers quoted in the readme (channel, inlet ramp, material constants,
$p_{amp}$, $p_{period}$) are configuration, not measurements.

Caveats — this demo needs attention before it can be trusted:

* **The inlet is not enforced.** The inlet `DirichletBC` object is built but
  never passed to the solver (`bcu` contains only the bottom and top walls), and
  `Um` $= 0.0$, so the cosine ramp described in the readme is identically zero.
* **The two `.geo` files disagree.** The readme names `turtle.geo`, but
  `generate_mesh.py` merges `turtle_solid.geo`; `turtle.geo` also lacks the
  physical lines $16/17$ that `main.py` integrates the pressure over, and its
  point coordinates differ from `turtle_solid.geo` by $0.01$ in $y$.
* The readme's neo-Hookean expression is not the $I_1$-form the code assembles,
  and the placement comment ("move right by $0.5$") does not match the code
  ($+1.0$ in $x$, then a $\times100$ scale).
* The logged `solid_force_norm` is $\int \mathbf{X}\cdot\mathbf{X}\,\mathrm{d}x$
  over the solid coordinates, not a force norm.
* The script prints `spine_dir.value` every step and assembles four forms per
  step over $600\,000$ steps, with no checkpointing.
* Outputs go to `~/afsi-data/...`, and `main.py` needs SwanLab plus an HTTPS
  counter call, so it does not run offline as shipped.
* `turtle_mesh.xdmf` is absent, and `main.py` loads it from a hard-coded path
  with no existence check.
