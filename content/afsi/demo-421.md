---
title: "421: Fish Swimming in a Circular Tank"
description: "A NACA-section fish with travelling-wave undulation swimming in a closed tank."
date: 2026-09-12
weight: 421
academic: true
demo_id: demo_421
category: Application
dimension: 2D
solid_model: "rigid NACA-section body (marker-enforced swimming kinematics)"
coupling: "multi-direct forcing (own AB2 fractional step), serial only"
reference: "DFIBMFoam — CircularFishSwimming"
status: Partial
---

## 1. Introduction

Where the fixed-cylinder case of [demo_339](/afsi/demo_339/) prescribes zero marker
velocity, here the desired velocity is the swimming kinematics itself,
$\mathbf{U}^d = (\mathbf{X}(t) - \mathbf{X}(t-\Delta t))/\Delta t$, fed into a
multi-direct-forcing loop. The solver is not `ChorinSolver`: the demo carries its
own AB2 / semi-implicit fractional-step scheme with a per-iteration force
accumulation in Python.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo421-setup.png" title="Figure 1. The closed tank, the prescribed circular path, and the travelling-wave midline of the body." >}}

The tank is $1.4 \times 1.4\,\mathrm{m}$ and **must start at the origin**
(`x0` $=$ `y0` $= 0$; see the kernel note in §5). The fish is
$0.1\,\mathrm{m}$ long and follows a circle of radius $0.3\,\mathrm{m}$ centred at
$(0.7, 0.7)$, i.e. the tank centre, with a cycle period of $37.7\,\mathrm{s}$.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
multi-direct-forcing formulation, and the kinematic constraint that imposes the
swimming motion (see the symbol table page).{{< /color >}}

The prescribed kinematics are: a travelling-wave midline
(`wavelength` $= 0.1\,\mathrm{m}$, `wave_period` $= 0.5\,\mathrm{s}$), a circular
orbit, and desired marker velocities
$\mathbf{U}^d = (\mathbf{X}(t)-\mathbf{X}(t-\Delta t))/\Delta t$.

### 2.3 Boundary and initial conditions

No-slip on all four walls of the closed tank, with one pressure degree of freedom
pinned at the corner; the body is driven by the marker forcing. The tank starts
from rest.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters (`configuration.py`, SI units). The tank must start at the origin — see the kernel note in §5.</p>

| Quantity | Code name | Value |
|---|---|---|
| Tank | `Lx`, `Ly` | $1.4 \times 1.4\,\mathrm{m}$, origin `x0` $=$ `y0` $= 0$ (required) |
| Density / viscosity | `rho`, `mu` | $1000\,\mathrm{kg\,m^{-3}}$ / $0.01\,\mathrm{Pa\,s}$ |
| Fish length | `fish_length` | $0.1\,\mathrm{m}$ |
| Undulation | `wavelength`, `wave_period` | $0.1\,\mathrm{m}$ / $0.5\,\mathrm{s}$ |
| Orbit | `orbit_radius`, `cycle_period`, `orbit_center` | $0.3\,\mathrm{m}$ / $37.7\,\mathrm{s}$ / $(0.7, 0.7)$ |
| Markers | `n_sections` | $120$ sections → $240$ surface markers ($\Delta s = 0.83\,\mathrm{mm}$) |
| Reynolds number printed | — | $\rho \cdot 0.15 \cdot L/\mu \approx 1500$ (hard-coded speed) |

{{< color "red" >}}TODO: define the Reynolds number actually realised by the
undulation kinematics, not the hard-coded printed value.{{< /color >}}

## 3. Numerical setup

The fluid grid is $280 \times 280$ ($h = 0.005\,\mathrm{m}$), the time step
$\Delta t = 0.001\,\mathrm{s}$ for $T = 1.0\,\mathrm{s}$ ($1000$ steps,
$\approx 2$ undulation periods), with $n_{iter} = 5$ direct-forcing iterations per
step and output every $20$ steps (`output/{velocity,pressure}.xdmf`,
`fish_trace.csv`). The solve is **single-process only** (see §5).

Environment overrides: `STEPS` (step count, resets $T$), `NX`, `NY` (grid).

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the body-centroid path and net travel (against the
prescribed orbit), the maximum fluid speed in the tank, and the thrust/lateral
force diagnostics — the latter are magnitude references only, because the force
integral does not converge (see §5).

### 4.2 Comparison with reference

{{< color "red" >}}TODO: comparison against the original DFIBMFoam run (path,
propulsion speed, thrust) — not archived.{{< /color >}}

| Quantity | AFSI | Reference (DFIBMFoam) | rel. err. |
| --- | --- | --- | --- |
| Net travel after two periods |  |  |  |
| Peak tank speed |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — the live run lowered the
resolution to $140^2$ to keep it short; no paired refinement exists.{{< /color >}}

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo421-results.png" title="Figure 2. Marker positions written by the run, and the prescribed circular path." >}}

**No results were archived** when these notes were first written — `output/` does
not exist in the repo and is git-ignored — so the fields and `fish_trace.csv` were
regenerated for the figures below. A live run was made as shipped except for the
fluid resolution, which was lowered to $N_x = N_y = 140$ to keep the run short:
$1000$ steps at $\Delta t = 0.001$, serial (the $\texttt{IBMesh}$ marker map is
not MPI-safe), $406\,\mathrm{s}$ of wall time.

{{< figure src="/afsi/demo421-fish-1s.png" title="Figure 3. The tank at $t = 0, 0.2, 0.4, 0.6, 0.8, 1$ s (top) with the fish silhouette from `fish_trace.csv`, and a near-body zoom (bottom). Each undulation cycle leaves a pair of counter-rotating eddies behind the body; the tank itself reacts with a slow return flow, which is what makes this a closed-domain case rather than a towed-fish one." >}}

{{< figure src="/afsi/demo421-path.png" title="Figure 4. Body-centroid path over the run and the net displacement. The tank is 14 body lengths across and one orbit is prescribed to take 37.7 s, so 1 s covers only 2.7 % of the circle." >}}

{{< figure src="/afsi/demo421-pyvista.png" title="Figure 5. The same instant rendered with PyVista: the whole tank and the near-body zoom, from the same mesh." >}}

<p class="tcaption">Table 2. The live run, $N = 140$, $t \le 1$ s.</p>

| Quantity | Value |
|---|---|
| Steps / wall time | $1000$, $406$ s serial |
| Net body travel | $0.0503\,\mathrm{m}$ = $0.50$ body lengths (mostly in $y$) |
| $\max\lvert u\rvert$ in the tank | $0.19\,\mathrm{m\,s^{-1}}$, against a body length of $0.1\,\mathrm{m}$ and an undulation period of $0.5\,\mathrm{s}$ |
| Body length / marker count | $0.0992\,\mathrm{m}$ from the traced outline, 240 markers |

The striking feature is how **local** the flow is: the fish is $7\,\%$ of the tank
across, so almost all of the kinetic energy sits within a body length of the surface
and the tank-scale motion is a slow return flow. Filling the prescribed 37.7 s orbit
would need roughly forty times the steps — about five hours at this resolution.

## 5. Discussion and limitations

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
* The readme's default-parameter table is **stale relative to the code**: it
  quotes $200$ sections ($400$ markers, $\Delta s \approx 0.5\,\mathrm{mm}$) and
  $N_x = N_y = 140$ with $h \approx 0.01\,\mathrm{m}$, while `configuration.py`
  sets $n_{sections} = 120$ (240 markers) and $N_x = N_y = 280$
  ($h = 0.005\,\mathrm{m}$).
* The readme cites the original implementation as an absolute path outside the
  repository (`/tmp/DFIBMFoam/.../IBM.C`).

## 6. Reproducibility

<p class="tcaption">Table 3. Files in the demo.</p>

| File | Role |
|---|---|
| `configuration.py` | Tank, fish, IBM and time-stepping parameters; `STEPS`/`NX`/`NY` overrides |
| `fish_geometry.py` | NACA thickness, travelling-wave midline, circular orbit, desired marker velocity |
| `main.py` | AB2 fractional-step solver + multi-direct forcing loop, XDMF/CSV output, thrust/lateral diagnostics |
| `readme.md` | Formulas, solver description, defaults, known limitations and the IBM kernel-bug write-up |

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_421
python main.py             # 1000 steps, T = 1 s ≈ 2 undulation periods
STEPS=100 python main.py   # smoke test
```

## References

{{< color "red" >}}TODO: references — add the DFIBMFoam / CircularFishSwimming
source the port is based on.{{< /color >}}
