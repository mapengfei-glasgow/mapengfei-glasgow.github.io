---
title: "400: Turtle Under Periodic Follower Pressure"
description: "An immersed turtle outline under a periodic follower pressure, with pinned head and tail."
date: 2026-09-12
weight: 400
academic: true
demo_id: demo_400
category: Application
dimension: 2D
solid_model: "inline isotropic + volumetric law, μ_s = λ_s = 10⁴ (CGS)"
coupling: "immersed boundary (`IBMesh`), serial only"
reference: "—"
status: Partial
---

## 1. Introduction

An immersed turtle outline — a narrow head and tail plus four limb lobes — sits in
a straight channel. The head and tail facets are held by a penalty, the limbs are
advected by the surrounding flow, and a periodic **follower pressure** is applied
along the spine direction. It is the demo that exercises tag-driven fixation,
traction that follows the deformed geometry, and a selectable pressure waveform.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo400-setup.png" title="Figure 1. The turtle outline (drawn from `turtle_solid.geo`), the pinned head and tail facets, and the follower pressure on the limb edges." >}}

The channel is $200 \times 100$ (CGS units, as in the source) and the turtle body
has a height of $33.8$; the outline is `turtle_solid.geo` ($40$ points,
characteristic length $0.01$, shifted and scaled $\times100$).

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes and the IB coupling terms (see the symbol table page).{{< /color >}}

The solid is assembled inline as isotropic + volumetric contributions,

$$
\mathbf{P}_{\text{iso}} = \mu_s J^{-1}\!\left(\mathbf{F} - \tfrac{I_1}{2}\mathbf{F}^{-\mathrm{T}}\right),
\qquad
\mathbf{P}_{\text{vol}} = \lambda_s \ln J\,\mathbf{F}^{-\mathrm{T}},
$$

with $\mu_s = \lambda_s = 1\times10^{4}$ ($\nu_s = 0.45$ is stored but unused).

### 2.3 Boundary and initial conditions

The head and tail facets (tag $15$) are held by a penalty
($\beta = 1\times10^{6}$). A periodic follower pressure is applied along the limb
edges (tags $16$/$17$; the direction is the tag-16→tag-17 centroid vector, updated
every step) with peak $p_{amp} = 100$, period $2.0\,\mathrm{s}$ and the
`fast_open` waveform (fast-phase fraction $0.1$). The inlet is intended to carry a
cosine ramp, but as shipped it is identically zero — see §5.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters (`configuration.py` and `main.py`). Units are CGS, as in the source.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx`, `Ly` | $200.0 \times 100.0$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Solid outline | `turtle_solid.geo` | $40$ points, characteristic length $0.01$; shifted then scaled $\times100$ |
| Solid law | inline | $\mathbf{P}_{\text{iso}} = \mu_s J^{-1}(\mathbf{F} - \tfrac{I_1}{2}\mathbf{F}^{-\mathrm{T}})$, $\mathbf{P}_{\text{vol}} = \lambda_s \ln J\,\mathbf{F}^{-\mathrm{T}}$ |
| Solid parameters | `mu_s`, `lambda_s` | $1\times10^{4}$ each ($\nu_s = 0.45$ is stored but unused) |
| Fixation | `beta`, tag $15$ | $1\times10^{6}$ penalty on the head/tail facets |
| Follower pressure | `p_amp`, `p_period` | $100.0$ over a period of $2.0\,\mathrm{s}$ |
| Waveform | `waveform`, `fast_ratio` | `fast_open` with a fast-phase fraction of $0.1$ |
| Traction facets | `dss(16)`, `dss(17)` | limb edges; the direction is the tag-16→tag-17 centroid vector, updated every step |

{{< color "red" >}}TODO: dimensionless numbers (Reynolds number, pressure-to-stiffness ratio) to put the CGS values in context.{{< /color >}}

## 3. Numerical setup

The fluid grid is $128 \times 64$ quadrilaterals (cell $1.5625^{2}$), with
`ChorinSolver` instantiated directly (the config's `nssolver` key is decorative),
$\Delta t = 5\times10^{-5}\,\mathrm{s}$ to $T = 30\,\mathrm{s}$
($600\,000$ steps) and output every $1000$ steps ($0.05\,\mathrm{s}$,
`TimeManager(fps=20)`). There are **no environment overrides** — the module has no
`os.environ` lookup at all.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the largest fluid velocity (against the load
waveform), the limb deflection in $y$, the solid volume change (a compression
check), and the follower-pressure waveform actually applied.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: comparison against a reference — none exists; the
quantitative statement to make first is the stability boundary of the explicit
coupling (smaller $\Delta t$ or sub-iterated coupling) at which the full period can
be run.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Peak limb deflection per cycle |  |  |  |
| Volume drift per cycle |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — one resolution only, and the coupling diverges before the first load period ends.{{< /color >}}

### 4.4 Flow and deformation fields, and where the run breaks

The directory has no offline entry point, so it was run through a small harness that
replaces `swanlab_init`/`swanlab_upload` with a no-op and a CSV logger — the same
approach `demo_339/_short_run/run_compare.py` uses. Two further fixes were needed
before it would start at all: `generate_mesh.py` imports `gmshio` from `dolfinx.io`
(renamed `dolfinx.io.gmsh` in 0.10), and `main.py` hard-codes `./turtle_mesh.xdmf`.
`STEPS` is now honoured as well. The run itself: $20000$ steps at
$\Delta t = 5\times10^{-5}$ ($t \le 1$ s of the $2$ s load period) on a
$128\times64$ grid, **2321 s** serial.

{{< figure src="/afsi/demo400-turtle-1s.png" title="Figure 3. The re-run at $t = 0, 0.1, 0.2, 0.35, 0.5, 0.75, 1$ s. Top: fluid velocity, which organises into four lobes around the flapping limbs. Bottom: pressure, which is a dipole across the body. The black outline is the deformed turtle mesh, drawn from `solid_coords_io`." >}}

{{< figure src="/afsi/demo400-history.png" title="Figure 4. The three diagnostics that matter. Left: the largest fluid velocity, on a log scale — it tracks the pressure ramp up to $t \approx 0.4$ s and then runs away to 28 m/s. Middle: the limb deflection (±0.6 m). Right: the applied follower pressure." >}}

<p class="tcaption">Table 2. The live run.</p>

| Quantity | Value |
|---|---|
| Steps / wall time | $20000$ steps, $2321$ s serial |
| Load | follower pressure on tags 16/17, fast-open waveform of period 2 s, peak 100 at $t = 0.2$ s |
| Inlet | **zero for the whole run** — `Um` $= 0.0$ *and* the inlet `DirichletBC` is never passed to the solver, so every motion in the fluid comes from the deforming body |
| Fluid velocity | $1.2\,\mathrm{m\,s^{-1}}$ at $t = 0.35$ s, $28\,\mathrm{m\,s^{-1}}$ at $t = 1$ s |
| Limb deflection | $+0.60 / -0.60\,\mathrm{m}$ in $y$, against a body height of $33.8$ |
| Volume | $319.93 \to 319.78$, i.e. $0.05\,\%$ compression |

**The first four snapshots are usable; the rest are not.** Up to $t \approx 0.4$ s the
response is physical and worth looking at: the pressure dipole across the body, the
four-lobe velocity pattern around the limbs, and the limbs deflecting by about 1.8 % of
the body height. Beyond that the solver runs away — by $t = 1$ s the fluid reaches
$28\,\mathrm{m\,s^{-1}}$ while the limb tips are moving at only $\approx 10^{-3}\,\mathrm{m\,s^{-1}}$,
a factor of $10^{4}$ larger than the kinematics can explain. That is the explicit
IB-FE coupling losing stability, not a physical result, and it happens well inside the
first load period. Running the documented 30 s / 600000 steps will need a smaller
$\Delta t$, sub-iterated coupling, or both.

{{< figure src="/afsi/demo400-results.png" title="Figure 2. The smoke run at $64 \times 32$ for 400 steps with the turtle outline overlaid, and the follower-pressure waveform the driver applies." >}}

## 5. Discussion and limitations

This demo needs attention before it can be trusted:

* **The inlet is not enforced.** The inlet `DirichletBC` object is built but
  never passed to the solver (`bcu` contains only the bottom and top walls), and
  `Um` $= 0.0$, so the cosine ramp described in the readme is identically zero.
* **The coupling diverges** inside the first load period (§4.4) — the explicit
  IB-FE scheme loses stability, and the documented $600\,000$-step run is out of
  reach without a smaller $\Delta t$ or sub-iterated coupling.
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
  with no existence check. **No results are archived**: the directory has no
  `.xdmf`, `.h5`, `.csv`, `.json` or image output, and none of the
  `~/afsi-data/demo-400/...` directories exist. The numbers quoted in the readme
  (channel, inlet ramp, material constants, $p_{amp}$, $p_{period}$) are
  configuration, not measurements.

## 6. Reproducibility

<p class="tcaption">Table 3. Files in the demo.</p>

| File | Role |
|---|---|
| `configuration.py` | All parameters, derived step count, output/experiment naming |
| `generate_mesh.py` | Gmsh mesh of `turtle_solid.geo` → `turtle_mesh.xdmf` (with cell/facet tags) |
| `main.py` | Driver: fluid, IB coupling, follower pressure, penalty fixation, XDMF output |
| `turtle_solid.geo` | The solid outline that is actually meshed (spine lines $16/17$, head–tail line $15$) |
| `turtle.geo` | A pygmsh-generated variant that also contains a fluid box; **not** referenced by the generator |
| `readme.md` | Chinese documentation of geometry, coupling, run command and outputs |

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_400
python generate_mesh.py     # produces turtle_mesh.xdmf next to main.py
python main.py              # or: mpirun -n <N> python main.py
```

## References

{{< color "red" >}}TODO: references — none cited; the follower-load benchmark motivation should be cited if one exists.{{< /color >}}
