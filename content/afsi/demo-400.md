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

{{< figure src="/afsi/demo400-setup.png" title="Figure 1. The turtle outline (drawn from `turtle_solid.geo`), the pinned head and tail facets, and the follower pressure on the limb edges." >}}

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

### 5.1 A live run ($t \le 1$ s), and where it breaks

The directory has no offline entry point, so it was run through a small harness that
replaces `swanlab_init`/`swanlab_upload` with a no-op and a CSV logger — the same
approach `demo_339/_short_run/run_compare.py` uses. Two further fixes were needed
before it would start at all: `generate_mesh.py` imports `gmshio` from `dolfinx.io`
(renamed `dolfinx.io.gmsh` in 0.10), and `main.py` hard-codes `./turtle_mesh.xdmf`.
`STEPS` is now honoured as well. The run itself: $20000$ steps at $\Delta t = 5\times10^{-5}$
($t \le 1$ s of the $2$ s load period) on a $128\times64$ grid, **2321 s** serial.

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
