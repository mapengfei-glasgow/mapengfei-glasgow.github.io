---
title: "demo_424 — tethered aorta in a box"
description: "Pressure-driven 2-D planar aorta verification case: full parameter set, open and occluded results, a mesh-refinement study, and a diagnosed IPCS solver defect with its fix."
date: 2026-09-12
weight: 2
---

Two cases share one geometry, one fluid, one tether model and one driving
condition; they differ only by a membrane that occludes the lumen.

| Case | Solid | Expected physics |
|---|---|---|
| `open` | two tethered wall strips | three parallel plane-Poiseuille channels (lumen + two outer gaps) driven by the end pressure difference |
| `closed` | the same strips **+ a full-occlusion membrane at mid-length** → the solid outline reads as the letter **H** | lumen chambers stagnant and isobaric, a jump of exactly Δp across the membrane, the outer gaps still carry the bypass flow |

This is a **pure solver-verification case**: the exact solution is known
analytically in both configurations, so every error metric below has a reference
value.

{{< figure src="/afsi/demo424-configuration.png" title="The two configurations. The box is half a cell longer than the aorta at each end, so the pressure Dirichlet nodes never coincide with a Lagrangian end node." >}}

## Geometry

2-D planar (plane-strain) idealisation: cutting the cylindrical aorta along a
plane through its axis turns the lumen into a parallel-plate channel and the wall
into two flat strips.

| Quantity | Value |
|---|---|
| aorta length `L_AORTA` | 0.1 m |
| lumen half-height `A_LUMEN` | 0.015 m (aorta radius) |
| wall thickness `T_WALL` | 0.002 m |
| box | `L_AORTA + h` long (half a cell beyond each open end), `1.5 × 2·A_LUMEN` = 0.045 m wide |
| outer fluid gap `GAP` | 0.0055 m per side |
| membrane | 0.002 m thick, at mid-length, spanning the lumen |

The grid is square, which fixes the usable resolutions: with `BOX_W = 0.045` and
`L_AORTA/BOX_W = 20/9`, `NY` must be a multiple of 9 — `NY ∈ {45, 90, 180}` give
`NX ∈ {101, 201, 401}`. Because `BOX_L = L_AORTA + h`, the imposed gradient
`Δp/BOX_L` depends slightly on the resolution (26.4005 Pa/m at NY = 45,
26.5318 Pa/m at NY = 90); the tables below use each level's own value.

## Physics

| Quantity | Value |
|---|---|
| fluid density | 1.0 (normalised) |
| fluid viscosity | 0.0035 Pa·s (blood-like), ν = 0.0035 m²/s |
| solid | **no constitutive law**; only a tether (volumetric spring) `f = β(X_ref − X)` |
| tether stiffness `β` | 1.0e7 N/m³ |
| driving difference, `open` | 0.02 mmHg = 2.666 Pa |
| driving difference, `closed` | 0.2 mmHg = 26.664 Pa (10×, see below) |
| ramp | linear, 0 → Δp over 0.05 s, then held to T = 0.4 s |
| dt | 2.0e-4 s |

Derived scales (open case): u_max = 0.848 m/s, u_mean = 0.565 m/s,
Re = ρ u_mean·2a/μ ≈ 4.9, viscous time a²/ν = 0.064 s. The flow is laminar and
only weakly inertial, so the fully developed profile is the exact Poiseuille
parabola and the entrance region (~1.5 cm, 15 % of the length) is excluded from
the comparisons.

**Why the closed case uses 10× the pressure difference.** In the open case the
transmural pressure vanishes at steady state (the lumen and the gap see the same
axial gradient), so the wall does not move and the case is a pure flow test. In
the closed case the flow is essentially zero, so nothing dissipates the driving
pressure — Δp is carried entirely by the membrane and its tether. The only
measurable response is the membrane displacement

    δ = Δp / (β · T_WALL)

which is 1.3e-4 m at 0.02 mmHg (100× smaller than a grid cell) but 1.3e-3 m at
0.2 mmHg. The 10× step makes the response measurable without moving the geometry
appreciably (δ ≈ 2 grid cells at NY = 90).

## Numerics

| Setting | Value |
|---|---|
| solver | `ChorinSolver` (explicit projection); `IPCSSolver` is available but unsuitable here — see [the solver note](#why-ipcssolver-fails-here-and-the-fix) |
| time step / end time | dt = 2.0e-4 s, T = 0.4 s → 2000 steps |
| pressure ramp | `RAMP_T` = 0.05 s, linear then held |
| fluid elements | `NX × NY` quadrilaterals, square cells (h = 1.0 mm at NY = 45, 0.5 mm at NY = 90) |
| velocity / pressure space | P2 / P1 |
| solid mesh | immersed strips, solid cell `h / SOLID_DIV` with `SOLID_DIV = 2` (solid cell 2.5e-4 m at NY = 90) |
| coupling | `IBMesh` + `IBInterpolation` (velocity interpolated to the solid, force spread back 4-point Peskin) |
| output | `plot/<case>_NY<n>/` — `pressure.xdmf`, `velocity.xdmf`, `verify.json` |

## Boundary conditions

* box side walls (the diameter direction): no-slip
* box open ends: **pressure Dirichlet** `p = p_in(t)` at x = 0 and `p = 0` at
  x = BOX_L, and **no velocity condition** — the natural condition there is zero
  traction

Prescribing pressure at a boundary is an essential (Dirichlet) condition on the
**pressure Poisson problem**, not a traction condition in the usual sense;
combined with the natural zero-traction condition of the momentum predictor it is
the projection-method realisation of a prescribed-normal-traction
(pressure-driven) open boundary. In this code it is exactly the `bcp` argument of
the solver. Because both ends carry Dirichlet data the pressure null space is
fixed and no gauge point is needed.

## Results

`dt = 2e-4 s`, `T = 0.4 s`, Chorin. Wall-clock on this machine: 26.1 min
(NY = 45) and 54.4 min (NY = 90) per case, single run, 16 threads.

### `open` — pressure field and flow rate

{{< figure src="/afsi/demo424-open-fields.png" title="Patent case at NY = 45. Left: the pressure field is linear in x. Middle: the lumen jet, with the smeared wall bands around it. Right: the lumen profile at x = 50 mm against the analytic Poiseuille parabola — the profiles sit on the same curve, the deficit is visible only in the numbers." >}}

| Metric | NY = 45 | NY = 90 | Analytic (per level) |
|---|---|---|---|
| fitted `G = −dp/dx` | 26.3856 Pa/m | 26.5147 Pa/m | 26.4005 / 26.5318 Pa/m |
| relative error in `G` | −5.6e-4 | −6.5e-4 | — |
| max deviation of p(x) from linear | 9.83e-5 Pa | 6.58e-5 Pa | 0 |
| `u_max` (interior window) | 0.8106 m/s | 0.8355 m/s | 0.8481 / 0.8523 m/s |
| `u_max` relative error | −4.42 % | −1.96 % | — |
| `Q_lumen` | 1.5852e-2 m²/s | 1.6540e-2 m²/s | 1.6962e-2 / 1.7045e-2 m²/s |
| `Q_lumen` relative error | −6.55 % | −2.96 % | — |
| `Q_gap` (both sides) | 1.9850e-4 m²/s | 2.1793e-4 m²/s | 2.0916e-4 / 2.1020e-4 m²/s |
| `Q_gap` relative error | −5.10 % | +3.68 % | — |
| lumen profile, relative L2 | 5.431 % | 2.625 % | — |
| lumen profile, \|e\|∞ | 3.691e-2 m/s | 1.722e-2 m/s | — |

The pressure field is essentially exact and the flow is fully developed (the
profile error is identical to four digits at x = 0.25/0.50/0.75 L), but the
**velocity is systematically ~5 % low**. That deficit is immersed-boundary
smearing: the 4-point Peskin kernel spreads the 2 mm wall over a ±2h band, so the
effective no-slip surface is displaced outward and the channel carries less flux.
The pointwise error peaks next to the wall and is small in the core, which is the
signature of an IB-interpolation error rather than a solver error.

### `closed` — the membrane holds the pressure, the wall leaks

{{< figure src="/afsi/demo424-closed-fields.png" title="Occluded case at NY = 45. The pressure is uniform at ≈ 26.6 Pa upstream and ≈ 0 downstream with a jump at the membrane; the velocity magnitude shows the bypass flow in the two outer gaps and the nearly stagnant lumen chambers (right: pressure along both channel centrelines)." >}}

| Metric | NY = 45 | NY = 90 | Target |
|---|---|---|---|
| held pressure jump (chamber means) | 26.2531 Pa | 26.5561 Pa | 26.6645 Pa (0.2 mmHg) |
| fraction of Δp held | 98.46 % | **99.59 %** | 100 % |
| upstream chamber p mean / std | 26.6147 / 0.0259 Pa | 26.6432 / 0.0110 Pa | isobaric |
| downstream chamber p mean / std | 0.3616 / 0.7811 Pa | 0.0871 / 0.2903 Pa | isobaric |
| leakage flux at x_d ± 4h (up / down) | 7.976e-4 / 6.239e-4 m²/s | 2.553e-4 / 3.606e-4 m²/s | 0 |
| `Q_gap` (both sides) | 5.250e-4 m²/s | 8.146e-4 m²/s | 2.0916e-3 / 2.1020e-3 m²/s |
| `Q_gap` relative error | −74.9 % | −61.2 % | — |
| membrane mean x-displacement δ | 2.489e-4 m | 1.154e-3 m | 1.333e-3 m = Δp/(β·t) |
| δ / expected | 18.7 % | **86.6 %** | 100 % |
| membrane tether force per depth | 0.1493 N/m | 0.6926 N/m | Δp·2a = 0.800 N/m |

Two findings worth flagging:

1. **The membrane holds 98.5 % of Δp at NY = 45 and 99.6 % at NY = 90** — the
   immersed occlusion works, and its error converges at second order.
2. **The wall leaks.** The outer gaps see the full end-to-end gradient while the
   sealed lumen sits at ≈ 0, so the downstream half of the wall carries a
   transmural pressure of a few Pa. The immersed 2 mm wall (only 2 cells at
   NY = 45) passes fluid: the downstream chamber is measurably not isobaric
   (std 0.78 Pa vs 0.026 Pa upstream), and only 25 % of the analytic bypass flux
   still flows in the gaps because the rest short-circuits into the lumen through
   the wall. At NY = 90 (wall 4 cells) that recovers to 39 %.

### Refinement NY = 45 → 90 (h = 1 mm → 0.5 mm)

Dollar-free convergence orders `p = log2(e₄₅ / e₉₀)`:

| `open` case | NY = 45 | NY = 90 | order |
|---|---|---|---|
| fitted `G`, relative error | −5.64e-4 | −6.46e-4 | ~0 (0.06 % at both) |
| max deviation of p(x) from linear | 9.83e-5 Pa | 6.58e-5 Pa | 0.58 |
| lumen profile, relative L2 | 5.431e-2 | 2.625e-2 | **1.05** |
| lumen profile, \|e\|∞ | 3.691e-2 m/s | 1.722e-2 m/s | 1.10 |
| `u_max`, relative error | −4.418e-2 | −1.965e-2 | **1.17** |
| `Q_lumen`, relative error | −6.55e-2 | −2.96e-2 | **1.14** |
| `Q_gap`, relative error | −5.10e-2 | +3.68e-2 | (sign change) |

| `closed` case | NY = 45 | NY = 90 | order |
|---|---|---|---|
| fraction of Δp held | 0.98457 | 0.99593 | — |
| relative error of the held jump | −1.543e-2 | −4.066e-3 | **1.92** |
| upstream chamber p std | 2.587e-2 Pa | 1.095e-2 Pa | 1.24 |
| downstream chamber p std | 7.811e-1 Pa | 2.903e-1 Pa | 1.43 |
| leakage flux at x_d − 4h | 7.976e-4 | 2.553e-4 m²/s | 1.64 |
| `Q_gap`, relative error | −7.49e-1 | −6.12e-1 | −0.29 |
| membrane δ / expected | 0.187 | 0.866 | — |

{{< figure src="/afsi/demo424-convergence.png" title="Left: the open-case error measures fall at first order in h while the pressure gradient stays flat at 0.06 %. Right: closed-case quantities normalised to be dimensionless." >}}

This confirms the diagnosis of the ~5 % deficit: it is an immersed-boundary
interpolation error, not a solver error, and it converges at **first order** in h.
The pressure field is unaffected — it stays exact to ~0.06 % at both resolutions.
The membrane's pressure-holding converges at second order and reaches **99.6 %**.
The wall leakage is the slow one: even at NY = 90 the gaps carry only 39 % of the
analytic bypass flux. If the closed case is meant to demonstrate a *sealed*
configuration, the wall needs to be better resolved (or thickened), not just the
membrane.

## Why `IPCSSolver` fails here, and the fix

### The mechanism

The strong form `ρ Du/Dt + ∇p − μ ∇²u − f = 0`, multiplied by a test function and
integrated over the domain, is

```
∫ ρ Du/Dt·v − ∫ p div(v) + ∫ μ grad(u):grad(v) − ∫ f·v
    + ∫_Γ [ p (v·n) − μ (grad(u)·n)·v ]  =  0
```

`IPCSSolver` keeps only the volume terms and **drops the whole boundary
integral**. Dropping it is equivalent to imposing the natural condition

```
μ grad(u)·n = p n        i.e.  zero total traction  σ·n = 0
```

on every boundary where no velocity is prescribed.

* At the **outlet** the pressure Dirichlet is `p = 0`, so zero traction is exactly
  right.
* At the **inlet** the pressure Dirichlet is `p = DP`, so zero traction is wrong
  by `DP`. The momentum predictor then tries to build a viscous stress of order
  `DP` inside a one-cell layer and produces a large spurious `div(u*)` there.

On its own that is a boundary-layer artifact. It becomes fatal because **IPCS
accumulates the pressure** (`p_ += phi`): the spurious divergence feeds straight
into `phi`, and once the flow settles (`div(u*) → 0`, hence `phi → 0`) the
corrupted pressure is frozen in place with nothing left to correct it.

`ChorinSolver` has no `p` in its momentum predictor, so its natural condition is
the homogeneous `μ grad(u)·n = 0` — exactly the physical interface condition for a
boundary whose outside only supplies pressure. That is why Chorin reproduces the
exact profile and IPCS does not.

### Evidence

Solid-free plane channel, `NY = 9`, ramp 0 → 2.666 Pa (`test_ipcs.py`),
**re-run for this page on 2026-09-13** (2–3 s per variant):

| variant | fitted G [Pa/m] | max abs(p − p_exact) | u_max rel. error |
|---|---|---|---|
| exact | 25.3947 | 0 | 0 |
| Chorin | 25.3949 | 2.08e-5 Pa | −5.14 % |
| IPCS, as shipped | 7.4107 | 2.95 Pa | −88.15 % |
| IPCS + restored traction term | **25.3944** | **7.43e-5 Pa** | −5.35 % |

A step boundary condition instead of the ramp gives the same broken result
(G = 7.40, 2.95 Pa), which rules out "the ramp increment is too small to be seen".

The instrumented pressure increment shows the collapse directly:

```
phi (as shipped) = [1.067e-2, -1.18e-3,  2.07e-3,  1.14e-3,  7.90e-4,  4.31e-4, 0]
phi (fixed)      = [1.067e-2,  1.017e-2, 9.66e-3,  8.13e-3,  5.59e-3,  3.05e-3, 0]
```

Only the fixed version propagates the boundary datum into the interior.

### The fix

Treat the pressure on the Dirichlet-pressure facets as known data and keep its
boundary term explicitly:

```python
F1 += dot(p_D * n, v) * ds(inlet_facets)      # n = FacetNormal(mesh)
```

The only condition then still imposed naturally is `μ grad(u)·n = 0`, the correct
interface condition for a boundary loaded by an external pressure `p_D`.
`ipcs_traction.py` implements this as `IPCSSolverTraction`, a subclass of
`IPCSSolver`, so the shared solver is left untouched:

```python
solver = IPCSSolverTraction(V, Q, bcu, bcp, dt, rho, mu, ds_inlet, p_const)
solver.p_traction.value = p_inlet(t)          # update every time step
```

Two cheaper alternatives, depending on what is needed:

* **Use Chorin** (the demo default). No code change; the pressure field is
  already exact. The only cost is Chorin's O(dt) steady-state pressure error when
  an immersed body force is present (see demo_423).
* **Drive with a body force** `f = G e_x` and put the pressure Dirichlet only at
  the outlet. Well posed for either solver, but then `p_` is only the
  incompressibility part of the pressure; the physical pressure is
  `p_phys = −G x + p_ + const`.

A separate, independent defect worth fixing in `IPCSSolver`: its velocity update
(`A3 = assemble_matrix(a3)`) is assembled **without** `bcu` and `set_bc` is never
called, so the corrected velocity does not re-satisfy no-slip at the walls.
`ChorinSolver` does apply `bcu` there.

## Reproducing

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_424

CASE=open   NY=45 python generate_mesh.py && CASE=open   NY=45 python main.py
CASE=closed NY=45 python generate_mesh.py && CASE=closed NY=45 python main.py

# solid-free control: isolates the open-boundary treatment from the IB coupling
CASE=open NY=45 T_END=0.2 python test_channel.py

# the IPCS diagnosis and its fix
SOLVER=chorin   NY=9 T_END=0.2 python test_ipcs.py
SOLVER=ipcs     NY=9 T_END=0.2 python test_ipcs.py
SOLVER=ipcs_fix NY=9 T_END=0.2 python test_ipcs.py
```

Environment overrides: `CASE`, `NY`, `SOLID_DIV`, `DT`, `T_END`, `RAMP_T`,
`SOLVER`, `DP_MMHG`, `BETA`, `DIAG=1`.

## Files

| File | Description |
|---|---|
| `configuration.py` | every shared parameter, plus `p_inlet(t)` and the expected membrane displacement |
| `generate_mesh.py` | structured quad mesh of the wall strips (+ membrane); asserts the solid area against the exact value |
| `main.py` | fluid box, pressure BCs, tether-only solid, IB coupling, time loop, diagnostics, final report |
| `verify.py` | analytic references, field sampling, error metrics |
| `test_channel.py` | solid-free plane-channel control (exact parallel-flow solution) |
| `test_ipcs.py` | IPCS vs Chorin instrumentation on the same channel |
| `ipcs_traction.py` | `IPCSSolverTraction` — the fixed IPCS variant |

## Status / open items

* NY = 180 (wall 8 cells) would confirm whether `Q_gap` also starts converging;
  at ~4× the NY = 90 cost that is a ~4 h run.
* The closed case needs a longer `T` (or a steady-state solver) to settle — it
  oscillates at both resolutions (max |u| between 0.30 and 0.40 m/s right to
  T = 0.4 s), whereas the open case converges monotonically.
* The solid meshes at NY = 45 and NY = 90 place the wall's inner surfaces at cell
  centres (7.5h) and on grid lines (15h) respectively; an IB method does not
  require alignment, but the two levels are not geometrically identical in that
  respect.
* The NY = 90 field snapshots were not retained on this machine (only their
  `verify.json`), so the field figures above are the NY = 45 runs.
