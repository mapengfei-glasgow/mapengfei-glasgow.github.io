---
title: "demo_421 — fish swimming in a circular tank (2-D)"
description: "demo_421: a FEniCSx port of DFIBMFoam's CircularFishSwimming — a NACA-section fish with travelling-wave undulation circling in a closed tank, driven by multi-direct forcing."
date: 2026-09-12
weight: 421
academic: true
---

## 1. What it is

A fish body with a NACA thickness distribution and a travelling-wave midline
swims around a circle inside a closed tank. Where the fixed-cylinder case of
[demo_339](/afsi/demo-339/) prescribes zero marker velocity, here the desired
velocity is the swimming kinematics itself,
$\mathbf{U}^d = (\mathbf{X}(t) - \mathbf{X}(t-\Delta t))/\Delta t$, fed into a
multi-direct-forcing loop. The solver is not `ChorinSolver`: the demo carries its
own AB2 / semi-implicit fractional-step scheme with a per-iteration force
accumulation in Python.

{{< figure src="/afsi/demo421-setup.png" title="Figure 1. The closed tank, the prescribed circular path, and the travelling-wave midline of the body." >}}

## 2. Configuration

<p class="tcaption">Table 1. Parameters (`configuration.py`, SI units). The tank must start at the origin — see the kernel note below.</p>

| Quantity | Code name | Value |
|---|---|---|
| Tank | `Lx`, `Ly` | $1.4 \times 1.4\,\mathrm{m}$, origin `x0` $=$ `y0` $= 0$ (required) |
| Fluid cells | `Nx`, `Ny` ← `NX`, `NY` | $280 \times 280$, $h = 0.005\,\mathrm{m}$ |
| Density / viscosity | `rho`, `mu` | $1000\,\mathrm{kg\,m^{-3}}$ / $0.01\,\mathrm{Pa\,s}$ |
| Boundaries | — | no-slip on all four walls, one pressure dof pinned at the corner |
| Fish length | `fish_length` | $0.1\,\mathrm{m}$ |
| Undulation | `wavelength`, `wave_period` | $0.1\,\mathrm{m}$ / $0.5\,\mathrm{s}$ |
| Orbit | `orbit_radius`, `cycle_period`, `orbit_center` | $0.3\,\mathrm{m}$ / $37.7\,\mathrm{s}$ / $(0.7, 0.7)$ |
| Markers | `n_sections` | $120$ sections → $240$ surface markers ($\Delta s = 0.83\,\mathrm{mm}$) |
| Direct forcing | `n_iter` | $5$ iterations per step |
| Time step / end time | `dt`, `T` | $0.001\,\mathrm{s}$ / $1.0\,\mathrm{s}$ ($1000$ steps) |
| Output | `out_interval` | every $20$ steps → `output/{velocity,pressure}.xdmf`, `fish_trace.csv` |
| Reynolds number printed | — | $\rho \cdot 0.15 \cdot L/\mu \approx 1500$ (hard-coded speed) |

Environment overrides: `STEPS` (step count, resets $T$), `NX`, `NY` (grid).

## 3. Files

| File | Role |
|---|---|
| `configuration.py` | Tank, fish, IBM and time-stepping parameters; `STEPS`/`NX`/`NY` overrides |
| `fish_geometry.py` | NACA thickness, travelling-wave midline, circular orbit, desired marker velocity |
| `main.py` | AB2 fractional-step solver + multi-direct forcing loop, XDMF/CSV output, thrust/lateral diagnostics |
| `readme.md` | Formulas, solver description, defaults, known limitations and the IBM kernel-bug write-up |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_421
python main.py             # 1000 steps, T = 1 s ≈ 2 undulation periods
STEPS=100 python main.py   # smoke test
```

## 5. Results and notes

{{< figure src="/afsi/demo421-results.png" title="Figure 2. Marker positions written by the run, and the prescribed circular path." >}}

**No results are archived** — `output/` does not exist and is git-ignored, so the
fields and `fish_trace.csv` must be regenerated. The readme's default-parameter
table is also **stale relative to the code**: it quotes $200$ sections
($400$ markers, $\Delta s \approx 0.5\,\mathrm{mm}$) and
$N_x = N_y = 140$ with $h \approx 0.01\,\mathrm{m}$, while `configuration.py`
sets $n_{sections} = 120$ (240 markers) and $N_x = N_y = 280$
($h = 0.005\,\mathrm{m}$).

Caveats, mostly documented by the readme itself:

* **IBM kernel origin bug.** The kernel computes grid indices as $X/\Delta h$
  without subtracting the domain origin while the mesh lookup uses
  $(x - x_0)/\Delta x$, so a non-origin domain shifts the coupling by
  $x_0/\Delta x$ cells. The workaround used here is to keep the tank at the
  origin and move the orbit centre to the tank centre; the real fix is a C++
  change plus a rebuild of `afsic_ext`.
* **Single process only** — the `IBMesh` mapping would have to be rewritten for
  MPI, although the driver still uses `allreduce` and rank-guarded writes.
* **The force integral does not converge.** Marker volumes are
  $\Delta V_l = \Delta s_l h \propto h$, so $\int \mathbf{f}_{\mathrm{IBM}}\,\mathrm{d}V$
  shrinks with refinement and the printed thrust/lateral forces are magnitude
  references only.
* **The C++ spreading replaces rather than accumulates** (`setitem`), so
  `main.py` spreads into a scratch field and accumulates in Python; without that
  only the last iteration's force survives and the flow is barely driven — the
  readme traces an earlier $u_{L2} \approx 0$ failure to exactly this.
* There is no interior mask for the slender body
  (`mask_interior` is accepted in the config and never read), and the
  marker/force loops are Python-level over $240$ markers inside the iteration
  loop.
* The readme cites the original implementation as an absolute path outside the
  repository (`/tmp/DFIBMFoam/.../IBM.C`).
