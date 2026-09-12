---
title: "Pressure-driven tethered aorta: a solver-verification case with an immersed occlusion"
description: "demo_424: two 2-D planar configurations with known exact solutions — full parameter set, measured results, a mesh-refinement study, and a diagnosed open-boundary defect in the IPCS solver."
date: 2026-09-12
weight: 2
academic: true
---

<div class="abstract">
<p><span class="abstract-title">Abstract—</span> Two planar configurations of a
tethered aorta in a box are used to verify the pressure-driven open-boundary
treatment, the immersed-boundary coupling and an immersed occlusion. The
configurations share a geometry, a fluid, a tether model and a driving condition,
and differ only by a membrane that seals the lumen at mid-length. Both have exact
solutions. The imposed pressure gradient is reproduced to 0.06 % at every
resolution, while the velocity field is systematically low by about 5 % at the
coarsest resolution; a refinement of *h* by a factor of two shows this deficit to
be first-order in *h*, the signature of immersed-interface smearing rather than a
solver error. The membrane holds 98.5 % of the applied pressure difference at the
coarse resolution and 99.6 % at the finer one, converging at second order. The
immersed wall, however, leaks: the outer bypass channels recover only 25 % → 39 %
of the analytic flow rate because fluid short-circuits through the two-cell wall.
Finally, the incremental pressure-correction solver shipped with AFSI is shown to
be unusable for a pressure-driven inflow, the mechanism is derived, and a fix that
restores the exact pressure gradient is verified.</p>
</div>

<p class="keywords"><strong>Keywords:</strong> immersed boundary method ·
pressure-driven open boundary · Chorin projection · incremental pressure
correction · mesh refinement · verification and validation</p>

## 1. Introduction

The case consists of two configurations that share one geometry, one fluid, one
tether model and one driving condition; they differ only by a membrane that
occludes the lumen. Since the exact solution is known analytically in both
configurations, every error metric reported below has a reference value, and the
case therefore serves as a pure solver-verification study.

<p class="tcaption">Table 1. The two configurations. The solid outline of the occluded case reads as the letter H.</p>

| Case | Solid | Expected physics |
|---|---|---|
| `open` | two tethered wall strips | three parallel plane-Poiseuille channels (lumen and two outer gaps) driven by the end pressure difference |
| `closed` | the same strips and a full-occlusion membrane at mid-length | lumen chambers stagnant and isobaric, a pressure jump of exactly Δp across the membrane, bypass flow still carried by the outer gaps |

{{< figure src="/afsi/demo424-configuration.png" title="Figure 1. The two configurations. The box is half a cell longer than the aorta at each end, so the pressure Dirichlet nodes never coincide with a Lagrangian end node." >}}

## 2. Configuration

### 2.1 Geometry and mesh

The configuration is a two-dimensional planar (plane-strain) idealisation: cutting
the cylindrical aorta along a plane through its axis turns the lumen into a
parallel-plate channel and the wall into two flat strips.

<p class="tcaption">Table 2. Geometry and mesh parameters.</p>

| Quantity | Symbol | Value |
|---|---|---|
| Aorta length | `L_AORTA` | 0.1 m |
| Lumen half-height | `A_LUMEN` | 0.015 m |
| Wall thickness | `T_WALL` | 0.002 m |
| Box length | `BOX_L` = `L_AORTA` + *h* | 0.1005 m (*h* = 1 mm), 0.10025 m (*h* = 0.5 mm) |
| Box width | `BOX_W` = 1.5 · 2`A_LUMEN` | 0.045 m |
| Outer fluid gap | `GAP` | 0.0055 m per side |
| Membrane thickness | `DISC_T` | 0.002 m, spanning the lumen at mid-length |
| Fluid cells | `NX` × `NY` | 101 × 45, 201 × 90 |
| Cell size | *h* = `BOX_W`/`NY` | 1.0 mm, 0.5 mm |
| Solid mesh | `SOLID_DIV` = 2 | solid cell *h*/2 |
| Coupling | — | `IBMesh` + `IBInterpolation`, four-point Peskin kernel |

The grid is square, which constrains the usable resolutions: with `BOX_W` =
0.045 m and `L_AORTA`/`BOX_W` = 20/9, `NY` must be a multiple of 9, so
`NY` ∈ {45, 90, 180} gives `NX` ∈ {101, 201, 401}. Because `BOX_L` =
`L_AORTA` + *h*, the imposed gradient Δp/`BOX_L` depends slightly on the
resolution — 26.4005 Pa m<sup>−1</sup> at `NY` = 45 and 26.5318 Pa m<sup>−1</sup>
at `NY` = 90. Each row of the results tables is compared against its own level's
value.

### 2.2 Fluid, solid and driving conditions

<p class="tcaption">Table 3. Material and driving parameters. The solid carries no constitutive law: it is held in place by a volumetric spring (tether) alone.</p>

| Quantity | Symbol | Value |
|---|---|---|
| Fluid density (normalised) | ρ | 1.0 |
| Fluid dynamic viscosity | μ | 3.5 × 10<sup>−3</sup> Pa s |
| Kinematic viscosity | ν = μ/ρ | 3.5 × 10<sup>−3</sup> m² s<sup>−1</sup> |
| Tether stiffness | β | 1.0 × 10<sup>7</sup> N m<sup>−3</sup> |
| Tether law | — | **f** = β (**X**<sub>ref</sub> − **X**) |
| Driving difference, `open` | Δp | 0.02 mmHg = 2.666 Pa |
| Driving difference, `closed` | Δp | 0.2 mmHg = 26.664 Pa |
| Ramp | — | linear, 0 → Δp over `RAMP_T` = 0.05 s, then held |
| End time | *T* | 0.4 s |
| Time step | Δ*t* | 2.0 × 10<sup>−4</sup> s (2000 steps) |

The derived scales of the patent case are u<sub>max</sub> = 0.848 m s<sup>−1</sup>,
u<sub>mean</sub> = 0.565 m s<sup>−1</sup>, Re = ρ u<sub>mean</sub> · 2*a*/μ ≈ 4.9
and a viscous time *a*²/ν = 0.064 s. The flow is laminar and only weakly
inertial, so the fully developed profile is the exact Poiseuille parabola and the
entrance region (≈ 1.5 cm, 15 % of the length) is excluded from the comparisons.

The occluded case is driven at ten times the pressure difference of the patent
case for a practical reason. In the patent case the transmural pressure vanishes
at steady state — the lumen and the gap see the same axial gradient — so the wall
does not move and the case is a pure flow test. In the occluded case the flow is
essentially zero, so nothing dissipates the driving pressure: Δp is carried
entirely by the membrane and its tether, and the only measurable response is the
membrane displacement given by the one-dimensional tether balance

<div class="equation"><span class="eqbody">δ = Δp / (β <em>t</em><sub>wall</sub>)</span><span class="eqno">(1)</span></div>

which is 1.3 × 10<sup>−4</sup> m at 0.02 mmHg — a hundred times smaller than a
grid cell — but 1.3 × 10<sup>−3</sup> m at 0.2 mmHg. The tenfold step makes the
response measurable without moving the geometry appreciably (δ ≈ 2 grid cells at
`NY` = 90).

### 2.3 Time integration

The explicit projection solver `ChorinSolver` is used throughout. The
incremental pressure-correction solver `IPCSSolver` is available in AFSI but is
unsuitable for this configuration as shipped; the reason, the evidence and a
verified remedy are given in Section 4.

### 2.4 Boundary conditions

* The box side walls (diameter direction) are no-slip.
* The box open ends carry a **pressure Dirichlet** condition, p = p<sub>in</sub>(*t*)
  at *x* = 0 and p = 0 at *x* = `BOX_L`, and **no velocity condition**; the
  natural condition there is zero traction.

Prescribing pressure on a boundary is an essential (Dirichlet) condition on the
pressure Poisson problem rather than a traction condition in the usual sense.
Combined with the natural zero-traction condition of the momentum predictor it is
the projection-method realisation of a prescribed-normal-traction
(pressure-driven) open boundary; in this code it is exactly the `bcp` argument of
the solver. Because both ends carry Dirichlet data the pressure null space is
fixed and no gauge point is required.

## 3. Results

All figures below are for Δ*t* = 2 × 10<sup>−4</sup> s and *T* = 0.4 s. The
wall-clock cost of a single run on the machine used here was 26.1 min
(`NY` = 45) and 54.4 min (`NY` = 90) per configuration.

### 3.1 Patent configuration

{{< figure src="/afsi/demo424-open-fields.png" title="Figure 2. Patent configuration at NY = 45. Left: the pressure field is linear in x. Centre: the lumen jet, with the smeared wall bands. Right: the lumen profile at x = 50 mm against the analytical Poiseuille parabola; the profiles coincide to the eye and the deficit appears only in the numbers." >}}

<p class="tcaption">Table 4. Patent configuration: measured quantities against their analytical values. The gradient is compared with that level's own Δp/BOX_L.</p>

| Quantity | `NY` = 45 | `NY` = 90 | Analytical (per level) |
|---|---|---|---|
| Fitted gradient *G* = −d*p*/d*x* | 26.3856 Pa m<sup>−1</sup> | 26.5147 Pa m<sup>−1</sup> | 26.4005 / 26.5318 Pa m<sup>−1</sup> |
| Relative error in *G* | −5.6 × 10<sup>−4</sup> | −6.5 × 10<sup>−4</sup> | — |
| Max deviation of p(x) from linear | 9.83 × 10<sup>−5</sup> Pa | 6.58 × 10<sup>−5</sup> Pa | 0 |
| u<sub>max</sub> (interior window) | 0.8106 m s<sup>−1</sup> | 0.8355 m s<sup>−1</sup> | 0.8481 / 0.8523 m s<sup>−1</sup> |
| Relative error in u<sub>max</sub> | −4.42 % | −1.96 % | — |
| Lumen flow rate *Q*<sub>lumen</sub> | 1.5852 × 10<sup>−2</sup> m² s<sup>−1</sup> | 1.6540 × 10<sup>−2</sup> m² s<sup>−1</sup> | 1.6962 / 1.7045 × 10<sup>−2</sup> m² s<sup>−1</sup> |
| Relative error in *Q*<sub>lumen</sub> | −6.55 % | −2.96 % | — |
| Gap flow rate *Q*<sub>gap</sub> (both sides) | 1.9850 × 10<sup>−4</sup> m² s<sup>−1</sup> | 2.1793 × 10<sup>−4</sup> m² s<sup>−1</sup> | 2.0916 / 2.1020 × 10<sup>−4</sup> m² s<sup>−1</sup> |
| Relative error in *Q*<sub>gap</sub> | −5.10 % | +3.68 % | — |
| Lumen profile, relative *L*₂ | 5.431 % | 2.625 % | — |
| Lumen profile, ‖e‖<sub>∞</sub> | 3.691 × 10<sup>−2</sup> m s<sup>−1</sup> | 1.722 × 10<sup>−2</sup> m s<sup>−1</sup> | — |

The pressure field is essentially exact and the flow is fully developed — the
profile error is identical to four significant digits at *x* = 0.25, 0.50 and
0.75 *L* — but the velocity is systematically about 5 % low. The deficit is
attributable to immersed-boundary smearing: the four-point Peskin kernel spreads
the 2 mm wall over a band of ±2*h*, so the effective no-slip surface is displaced
outward and the channel carries less flux. The pointwise error peaks next to the
wall and is small in the core, which is the signature of an interpolation error
rather than a solver error.

### 3.2 Occluded configuration

{{< figure src="/afsi/demo424-closed-fields.png" title="Figure 3. Occluded configuration at NY = 45. The pressure is uniform at approximately 26.6 Pa upstream and approximately 0 downstream, with a jump at the membrane; the velocity magnitude shows the bypass flow in the two outer gaps and the nearly stagnant lumen chambers. Right: pressure along both channel centrelines." >}}

<p class="tcaption">Table 5. Occluded configuration: pressure holding, chamber uniformity and leakage.</p>

| Quantity | `NY` = 45 | `NY` = 90 | Target |
|---|---|---|---|
| Held pressure jump (chamber means) | 26.2531 Pa | 26.5561 Pa | 26.6645 Pa (0.2 mmHg) |
| Fraction of Δp held | 98.46 % | 99.59 % | 100 % |
| Upstream chamber: mean / standard deviation | 26.6147 / 0.0259 Pa | 26.6432 / 0.0110 Pa | isobaric |
| Downstream chamber: mean / standard deviation | 0.3616 / 0.7811 Pa | 0.0871 / 0.2903 Pa | isobaric |
| Leakage flux at *x*<sub>d</sub> ± 4*h* (upstream / downstream) | 7.976 / 6.239 × 10<sup>−4</sup> m² s<sup>−1</sup> | 2.553 / 3.606 × 10<sup>−4</sup> m² s<sup>−1</sup> | 0 |
| Gap flow rate *Q*<sub>gap</sub> | 5.250 × 10<sup>−4</sup> m² s<sup>−1</sup> | 8.146 × 10<sup>−4</sup> m² s<sup>−1</sup> | 2.0916 / 2.1020 × 10<sup>−3</sup> m² s<sup>−1</sup> |
| Relative error in *Q*<sub>gap</sub> | −74.9 % | −61.2 % | — |
| Membrane displacement δ | 2.489 × 10<sup>−4</sup> m | 1.154 × 10<sup>−3</sup> m | 1.333 × 10<sup>−3</sup> m (Eq. 1) |
| δ relative to Eq. 1 | 18.7 % | 86.6 % | 100 % |
| Membrane tether force per unit depth | 0.1493 N m<sup>−1</sup> | 0.6926 N m<sup>−1</sup> | Δp · 2*a* = 0.800 N m<sup>−1</sup> |

Two findings deserve emphasis.

1. **The membrane holds the pressure.** It sustains 98.5 % of Δp at the coarse
   resolution and 99.6 % at the fine one, and its error converges at second order,
   so the immersed occlusion works as intended.
2. **The wall leaks.** The outer gaps see the full end-to-end gradient while the
   sealed lumen sits at approximately zero, so the downstream half of the wall
   carries a transmural pressure of a few pascals. The immersed 2 mm wall — only
   two cells thick at `NY` = 45 — passes fluid: the downstream chamber is
   measurably not isobaric (standard deviation 0.78 Pa against 0.026 Pa upstream),
   and only 25 % of the analytical bypass flux still flows in the gaps because the
   remainder short-circuits into the lumen through the wall. At `NY` = 90, where
   the wall is four cells thick, the recovery is to 39 %.

The membrane reaches only 18.7 % of the displacement predicted by Eq. 1 at
`NY` = 45, i.e. that run is not settled: the tether force is 0.149 N m<sup>−1</sup>
against a pressure force of 0.800 N m<sup>−1</sup>. At `NY` = 90 the same run
reaches 86.6 % (δ = 1.154 × 10<sup>−3</sup> m, tether force
0.693 N m<sup>−1</sup>), close to the analytical tether equilibrium. The residual
gap is consistent with the occluded case never fully settling in time: max |**u**|
oscillates between 0.30 and 0.40 m s<sup>−1</sup> up to *T* = 0.4 s at both
resolutions, whereas the patent case converges monotonically.

### 3.3 Mesh refinement

Refining *h* from 1.0 mm to 0.5 mm gives the dollar-free convergence orders
*p* = log₂(e₄₅/e₉₀) listed below.

<p class="tcaption">Table 6. Patent configuration: observed convergence orders between NY = 45 and NY = 90.</p>

| Quantity | `NY` = 45 | `NY` = 90 | Order |
|---|---|---|---|
| Fitted gradient *G*, relative error | −5.64 × 10<sup>−4</sup> | −6.46 × 10<sup>−4</sup> | ≈ 0 |
| Max deviation of p(x) from linear | 9.83 × 10<sup>−5</sup> Pa | 6.58 × 10<sup>−5</sup> Pa | 0.58 |
| Lumen profile, relative *L*₂ | 5.431 × 10<sup>−2</sup> | 2.625 × 10<sup>−2</sup> | **1.05** |
| Lumen profile, ‖e‖<sub>∞</sub> | 3.691 × 10<sup>−2</sup> m s<sup>−1</sup> | 1.722 × 10<sup>−2</sup> m s<sup>−1</sup> | 1.10 |
| u<sub>max</sub>, relative error | −4.418 × 10<sup>−2</sup> | −1.965 × 10<sup>−2</sup> | **1.17** |
| *Q*<sub>lumen</sub>, relative error | −6.55 × 10<sup>−2</sup> | −2.96 × 10<sup>−2</sup> | **1.14** |
| *Q*<sub>gap</sub>, relative error | −5.10 × 10<sup>−2</sup> | +3.68 × 10<sup>−2</sup> | sign change |

<p class="tcaption">Table 7. Occluded configuration: observed convergence orders between NY = 45 and NY = 90.</p>

| Quantity | `NY` = 45 | `NY` = 90 | Order |
|---|---|---|---|
| Fraction of Δp held | 0.98457 | 0.99593 | — |
| Relative error of the held jump | −1.543 × 10<sup>−2</sup> | −4.066 × 10<sup>−3</sup> | **1.92** |
| Upstream chamber pressure standard deviation | 2.587 × 10<sup>−2</sup> Pa | 1.095 × 10<sup>−2</sup> Pa | 1.24 |
| Downstream chamber pressure standard deviation | 7.811 × 10<sup>−1</sup> Pa | 2.903 × 10<sup>−1</sup> Pa | 1.43 |
| Leakage flux at *x*<sub>d</sub> − 4*h* | 7.976 × 10<sup>−4</sup> m² s<sup>−1</sup> | 2.553 × 10<sup>−4</sup> m² s<sup>−1</sup> | 1.64 |
| *Q*<sub>gap</sub>, relative error | −7.49 × 10<sup>−1</sup> | −6.12 × 10<sup>−1</sup> | −0.29 |
| Membrane δ relative to Eq. 1 | 0.187 | 0.866 | — |

{{< figure src="/afsi/demo424-convergence.png" title="Figure 4. Left: the patent-case error measures fall at first order in h while the pressure gradient remains flat at 0.06 %. Right: occluded-case quantities, normalised so that all four are dimensionless." >}}

Tables 6 and 7 confirm the diagnosis of the velocity deficit: it is an
immersed-boundary interpolation error, not a solver error, and it converges at
**first order** in *h*. The pressure field is unaffected and remains exact to
about 0.06 % at both resolutions. The membrane's pressure holding converges at
second order and reaches 99.6 %. The wall leakage is the slow quantity: even at
`NY` = 90 the gaps carry only 39 % of the analytical bypass flux. If the occluded
configuration is to demonstrate a sealed lumen, the wall — not only the
membrane — must be better resolved or thickened.

## 4. An open-boundary defect in the IPCS solver

### 4.1 Mechanism

Multiplying the strong form ρ D**u**/D*t* + ∇p − μ∇²**u** − **f** = 0 by a test
function and integrating over the domain gives

<div class="equation"><span class="eqbody">∫ ρ (D<strong>u</strong>/D<em>t</em>)·<strong>v</strong> − ∫ p div <strong>v</strong> + ∫ μ ∇<strong>u</strong> : ∇<strong>v</strong> − ∫ <strong>f</strong>·<strong>v</strong> + ∫<sub>Γ</sub> [ p (<strong>v</strong>·<strong>n</strong>) − μ (∇<strong>u</strong>·<strong>n</strong>)·<strong>v</strong> ] = 0</span><span class="eqno">(2)</span></div>

`IPCSSolver` retains the volume terms and **drops the entire boundary integral**.
Doing so is equivalent to imposing the natural condition

<div class="equation"><span class="eqbody">μ ∇<strong>u</strong>·<strong>n</strong> = p <strong>n</strong>, i.e. zero total traction σ·<strong>n</strong> = 0</span><span class="eqno">(3)</span></div>

on every boundary where no velocity is prescribed. At the outlet the pressure
Dirichlet is p = 0, so zero traction is exactly right. At the inlet the pressure
Dirichlet is p = Δp, so zero traction is wrong by Δp: the momentum predictor then
attempts to build a viscous stress of order Δp inside a one-cell layer and
produces a large spurious div **u**\* there.

On its own this is a boundary-layer artefact. It becomes fatal because `IPCS`
**accumulates** the pressure (p_ += φ): the spurious divergence feeds directly
into φ, and once the flow settles (div **u**\* → 0, hence φ → 0) the corrupted
pressure is frozen in place with nothing left to correct it.

`ChorinSolver` carries no p in its momentum predictor, so its natural condition is
the homogeneous μ∇**u**·**n** = 0 — exactly the physical interface condition for a
boundary whose exterior only supplies pressure. That is why Chorin reproduces the
exact profile and IPCS does not.

### 4.2 Evidence

A solid-free plane channel at `NY` = 9 with a ramp 0 → 2.666 Pa (`test_ipcs.py`),
re-run for this report on 2026-09-13 at 2–3 s per variant:

<p class="tcaption">Table 8. Solid-free plane channel, NY = 9: fitted pressure gradient and velocity error per solver variant.</p>

| Variant | Fitted *G* (Pa m<sup>−1</sup>) | max \|p − p<sub>exact</sub>\| | Relative error in u<sub>max</sub> |
|---|---|---|---|
| Exact | 25.3947 | 0 | 0 |
| Chorin | 25.3949 | 2.08 × 10<sup>−5</sup> Pa | −5.14 % |
| IPCS, as shipped | 7.4107 | 2.95 Pa | −88.15 % |
| IPCS with restored traction term | **25.3944** | **7.43 × 10<sup>−5</sup> Pa** | −5.35 % |

Imposing the full Δp in a single step instead of ramping it yields the same
broken result (*G* = 7.40 Pa m<sup>−1</sup>, 2.95 Pa), which rules out the
explanation that the ramp increment is too small to be resolved.

The instrumented pressure increment along the centreline shows the collapse
directly; only the fixed version propagates the boundary datum into the interior.

```text
phi (as shipped) = [1.067e-2, -1.18e-3,  2.07e-3,  1.14e-3,  7.90e-4,  4.31e-4, 0]
phi (fixed)      = [1.067e-2,  1.017e-2, 9.66e-3,  8.13e-3,  5.59e-3,  3.05e-3, 0]
```

### 4.3 Remedy

Treating the pressure on the Dirichlet-pressure facets as known data and
retaining its boundary term explicitly,

```python
F1 += dot(p_D * n, v) * ds(inlet_facets)      # n = FacetNormal(mesh)
```

leaves μ∇**u**·**n** = 0 as the only naturally imposed condition — the correct
interface condition for a boundary loaded by an external pressure p<sub>D</sub>.
`ipcs_traction.py` implements this as `IPCSSolverTraction`, a subclass of
`IPCSSolver`, so the shared solver is left untouched:

```python
solver = IPCSSolverTraction(V, Q, bcu, bcp, dt, rho, mu, ds_inlet, p_const)
solver.p_traction.value = p_inlet(t)          # update every time step
```

Two cheaper alternatives should be noted.

1. **Use Chorin** (the default of this demo). No code change is required and the
   pressure field is already exact; the only cost is Chorin's O(Δ*t*) steady-state
   pressure error when an immersed body force is present (see
   [demo_423](/afsi/demo-423/)).
2. **Drive with a body force** **f** = *G* **e**<sub>x</sub> and impose the
   pressure Dirichlet only at the outlet. This is well posed for either solver,
   but p_ then holds only the incompressibility part of the pressure; the physical
   pressure is p<sub>phys</sub> = −*G x* + p_ + const.

Finally, a separate and independent defect in `IPCSSolver` is worth fixing: its
velocity update (`A3 = assemble_matrix(a3)`) is assembled **without** `bcu`, and
`set_bc` is never called, so the corrected velocity does not re-satisfy no-slip at
the walls. `ChorinSolver` does apply `bcu` in the corresponding step.

## 5. Reproducibility

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_424

CASE=open   NY=45 python generate_mesh.py && CASE=open   NY=45 python main.py
CASE=closed NY=45 python generate_mesh.py && CASE=closed NY=45 python main.py

# solid-free control: isolates the open-boundary treatment from the IB coupling
CASE=open NY=45 T_END=0.2 python test_channel.py

# the IPCS diagnosis and its remedy
SOLVER=chorin   NY=9 T_END=0.2 python test_ipcs.py
SOLVER=ipcs     NY=9 T_END=0.2 python test_ipcs.py
SOLVER=ipcs_fix NY=9 T_END=0.2 python test_ipcs.py
```

The environment variables `CASE`, `NY`, `SOLID_DIV`, `DT`, `T_END`, `RAMP_T`,
`SOLVER`, `DP_MMHG`, `BETA` and `DIAG` override the values of Tables 2 and 3.

## 6. Summary and open items

The imposed pressure gradient is reproduced to 0.06 % at both resolutions, the
velocity field converges to the analytical Poiseuille solution at first order in
*h* with a leading immersed-interface error of about 5 %, and the immersed
membrane holds 98.5 % → 99.6 % of the applied pressure difference at second-order
convergence. The remaining discrepancies all trace to a single cause — the
immersed wall is only two to four cells thick — which also limits the recovery of
the analytical bypass flow rate to 25 % → 39 %. The IPCS defect documented in
Section 4 makes that solver unusable for a pressure-driven inflow; the verified
remedy restores the exact gradient.

Open items:

* `NY` = 180 (wall eight cells thick) would establish whether *Q*<sub>gap</sub>
  also begins to converge; at roughly four times the cost of `NY` = 90 this is an
  approximately four-hour run.
* The occluded case needs a longer *T*, or a steady-state solver, to settle; it
  oscillates at both resolutions.
* The solid meshes at `NY` = 45 and `NY` = 90 place the inner wall surfaces at
  cell centres (7.5*h*) and on grid lines (15*h*) respectively. An immersed method
  does not require alignment, but the two levels are not geometrically identical
  in this respect.
* The `NY` = 90 field snapshots were not retained on this machine (only their
  verification summaries), so the field figures are the `NY` = 45 runs.

<div class="references">

**References**

1. Ma, P., Cai, L., Wang, X., Gao, H. *AFSI: Automated Fluid-Structure
   Interaction Solver Development for Nonlinear Solid Mechanics.*
   arXiv:2509.00014 (2025).
2. Chorin, A. J. *Numerical solution of the Navier–Stokes equations.*
   Mathematics of Computation 22 (1968) 745–762.
3. Peskin, C. S. *The immersed boundary method.* Acta Numerica 11 (2002) 479–517.
4. AFSI source `afsic/demo/demo_424` (`configuration.py`, `generate_mesh.py`,
   `main.py`, `verify.py`, `test_channel.py`, `test_ipcs.py`, `ipcs_traction.py`).

</div>
