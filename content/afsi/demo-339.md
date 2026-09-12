---
title: "demo_339 — flow past a cylinder, four ways"
description: "demo_339: the DFG 2D-3 benchmark (Re = 100) solved with no cylinder, a body-fitted mesh, immersed-boundary finite elements and multi-direct forcing."
date: 2026-09-12
weight: 339
academic: true
---

## 1. What it is

The DFG benchmark 2D-3 — channel flow past a cylinder at $\mathrm{Re} = 100$ —
solved four ways on the same SI-unit geometry, so that the treatments of the
body can be compared directly:

| Case | Directory | Treatment of the cylinder |
|---|---|---|
| 1 | `1-no-cylinder/` | none — baseline channel |
| 2 | `2-body-fitted/` | a hole in a Gmsh mesh with a no-slip Dirichlet condition on it |
| 3 | `3-ibfe/` | an immersed near-rigid neo-Hookean disc ($\mu_s = 7.7\times10^{10}$ Pa) held by a $\beta = 10^{12}$ penalty |
| 4 | `4-multi-direct-forcing/` | multi-direct forcing with a rigid marker set and interior masking |

## 2. Configuration

<p class="tcaption">Table 1. Shared parameters (SI units). Cases 1, 3 and 4 use the same uniform grid; case 2 replaces it with a Gmsh mesh.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $2.2 \times 0.41\,\mathrm{m}$ |
| Cylinder centre | `cx`, `cy` | $(0.2, 0.2)\,\mathrm{m}$ |
| Cylinder radius | `R` | $0.05\,\mathrm{m}$, i.e. $D = 0.1\,\mathrm{m}$ |
| Mean inlet velocity | `Um` | $1.0\,\mathrm{m\,s^{-1}}$ |
| Density / viscosity | `rho`, `mu` | $1000\,\mathrm{kg\,m^{-3}}$ / $1.0\,\mathrm{Pa\,s}$ |
| Reynolds number | $\mathrm{Re} = \rho U_m D/\mu$ | $100$ |
| Grid | `Nx` × `Ny` | $220 \times 41$, $h \approx 0.01\,\mathrm{m}$ |
| Time step / end time | `dt`, `T` | $0.001\,\mathrm{s}$ / $10\,\mathrm{s}$ ($10^4$ steps) |
| Inlet profile | `TurekInlet` | $u_x = 1.5\,U_m\,y(H-y)/(H/2)^2$, ramp $t_{ramp} = 2\,\mathrm{s}$ |
| Body-fitted mesh | `channel_hole.msh` | $10\,762$ nodes, $21\,524$ elements, $\text{size} \le 0.01\,\mathrm{m}$ |
| IB-FE disc mesh | `cylinder_solid.xdmf` | Gmsh, size $0.002$–$0.005\,\mathrm{m}$ (must be generated) |
| Direct-forcing markers | `n_markers`, `n_iter` | $128$ rim markers ($\Delta s \approx 2.45\,\mathrm{mm}$), $10$ iterations |

Cases 1–3 use `ChorinSolver` with $\mathrm{P2}/\mathrm{P1}$ elements; case 4 uses
the hand-written AB2 fractional step with iterated direct forcing and an interior
mask that zeroes the velocity inside $r < R$.

Environment overrides: `STEPS` in case 4's configuration and in
`_short_run/run_compare.py` (default $300$ steps, which recomputes $T$).

## 3. Files

| File | Role |
|---|---|
| `README.md` | Master document: method table, shared parameters, governing equations, short-run validation, dolfinx-0.10 fixes, drag-coefficient study |
| `1-no-cylinder/` | Baseline channel driver + configuration |
| `2-body-fitted/` | `channel_hole.geo`, archived `channel_hole.msh`, generator and driver |
| `3-ibfe/` | `cylinder_solid.geo`, generator, IB-FE driver with the penalty-fixed disc |
| `4-multi-direct-forcing/` | AB2 + multi-direct-forcing driver, configuration, readme |
| `_short_run/` | Offline harness that runs all four in one process and prints `[RESULT]` lines; `summary.txt` archives the four-way comparison |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_339

cd 1-no-cylinder            && python main.py
cd ../2-body-fitted         && python main.py    # mesh already in the repo
cd ../3-ibfe                && python generate_mesh.py && python main.py
cd ../4-multi-direct-forcing && python main.py

STEPS=300 python _short_run/run_compare.py all   # offline four-way comparison
```

## 5. Results and notes

Archived results are the short-run summary and the numbers in the readmes:

| Quantity | Value | Source |
|---|---|---|
| 300-step $u_{L2}$ / $p_{L2}$: no-cylinder, body-fitted, IB-FE, mdf | $0.002728$ / $208\,905$; $0.002792$ / $207\,765$; $0.002728$ / $208\,905$; $0.002828$ / $0.224956$ | `_short_run/summary.txt` |
| Drag coefficient, $2500$ steps ($t = 2.5\,\mathrm{s}$): body-fitted / mdf disc / mdf boundary | $2.664$ / $4.091$ / $4.388$ | `4-multi-direct-forcing/readme.md:80-84` |
| Quasi-steady wake ($t > 6\,\mathrm{s}$, mdf) | $\mathrm{Cd} \approx 2.53$, $\mathrm{St} \approx 0.52$ against the reference $\mathrm{Cd} \approx 5.57$, $\mathrm{St} \approx 0.3$ | `4-multi-direct-forcing/readme.md:161-171` |
| Body-fitted, $10\,\mathrm{s}$ | wake spikes to $-5811\,\mathrm{m\,s^{-1}}$, Cd spikes to $10^{91}$ after $t > 6.8\,\mathrm{s}$ | `4-multi-direct-forcing/readme.md:175-180` |

The readme's own conclusion is that the **velocity field converges but the
volume-force-integral drag does not**: marker volumes sum to $2\pi r h \propto h$,
so $\mathrm{Cd}$ from $\int \mathbf{f}_{\mathrm{IB}}\,\mathrm{d}V$ is
grid-dependent (the resolution study gives $0.439$, $0.268$, $0.157$ for
$110\times21$, $220\times41$, $440\times82$ against a reference $0.292$). A
control-volume momentum balance is recommended instead.

Caveats:

* `README.md` states that `cylinder_solid.xdmf` already exists for case 3, but no
  such file is archived — `generate_mesh.py` must run first.
* Three drivers embed a SwanLab API key and require network access;
  `_short_run/run_compare.py` replaces those calls for offline runs.
* The marker-id conventions differ between cases (case 1/3 use
  $14/12/11/13$ for inlet/outlet/bottom/top, case 2's Gmsh tags are
  $11/12/13/14$, case 4 uses the library constants $1..4$).
* Case 4's drag coefficient omits the density factor even though the
  configuration sets $\rho = 1000$, so whether the archived $\mathrm{Cd}$ values
  are density-normalised is unclear.
* The IB-FE case is inherently stiff: the disc drifts $\approx 9\times10^{-4}\,\mathrm{m}$
  over $300$ steps and the solid force becomes `NaN` after $\approx 200$ steps.
