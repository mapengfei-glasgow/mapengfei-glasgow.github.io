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
coupling: "immersed boundary (`IBMesh`)"
reference: "—"
status: Partial
---

## 1. Introduction

An immersed turtle outline — a narrow head and tail plus four limb lobes — sits in
a straight channel. The head and tail facets are held by a penalty, the limbs are
advected by the surrounding flow, and a periodic **follower pressure** is applied
along the spine direction. The case exercises tag-driven fixation, traction that
follows the deformed geometry, and a selectable pressure waveform.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo400-setup.png" title="Figure 1. The turtle outline, the pinned head and tail facets, and the follower pressure on the limb edges." >}}

The channel is $200 \times 100$ (CGS units, as in the source) and the turtle body
has a height of $33.8$; the outline is a $40$-point curve, shifted and scaled to
this size.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes and
the IB coupling terms (see the symbol table page).{{< /color >}}

The solid is assembled inline as isotropic + volumetric contributions,

$$
\mathbf{P}_{\text{iso}} = \mu_s J^{-1}\!\left(\mathbf{F} - \tfrac{I_1}{2}\mathbf{F}^{-\mathrm{T}}\right),
\qquad
\mathbf{P}_{\text{vol}} = \lambda_s \ln J\,\mathbf{F}^{-\mathrm{T}},
$$

with $\mu_s = \lambda_s = 1\times10^{4}$.

### 2.3 Boundary and initial conditions

The head and tail facets are held by a penalty ($\beta = 1\times10^{6}$). A
periodic follower pressure is applied along the limb edges; the direction is the
limb-edge centroid axis, updated every step — the traction follows the deformed
geometry. The load has peak $p_{amp} = 100$, period $2.0\,\mathrm{s}$ and a
`fast_open` waveform (fast-phase fraction $0.1$). The inlet is intended to carry a
cosine ramp, but as configured it is identically zero — see §5.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. Units are CGS.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Channel | `Lx`, `Ly` | $200.0 \times 100.0$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Solid outline | — | $40$ points, characteristic length $0.01$; shifted then scaled $\times100$ |
| Solid law | inline | $\mathbf{P}_{\text{iso}} = \mu_s J^{-1}(\mathbf{F} - \tfrac{I_1}{2}\mathbf{F}^{-\mathrm{T}})$, $\mathbf{P}_{\text{vol}} = \lambda_s \ln J\,\mathbf{F}^{-\mathrm{T}}$ |
| Solid parameters | `mu_s`, `lambda_s` | $1\times10^{4}$ each |
| Fixation | `beta` | $1\times10^{6}$ penalty on the head/tail facets |
| Follower pressure | `p_amp`, `p_period` | $100.0$ over a period of $2.0\,\mathrm{s}$ |
| Waveform | `waveform`, `fast_ratio` | `fast_open` with a fast-phase fraction of $0.1$ |

{{< color "red" >}}TODO: dimensionless numbers (Reynolds number,
pressure-to-stiffness ratio) to put the CGS values in context.{{< /color >}}

## 3. Numerical setup

The fluid grid is $128 \times 64$ quadrilaterals (cell $1.5625^{2}$), with a
Chorin projection solver, $\Delta t = 5\times10^{-5}\,\mathrm{s}$ to
$T = 30\,\mathrm{s}$ ($600\,000$ steps) and output every $1000$ steps
($0.05\,\mathrm{s}$).

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

{{< color "red" >}}TODO: grid and time-step sensitivity — one resolution only, and
the coupling diverges before the first load period ends.{{< /color >}}

### 4.4 Flow and deformation fields, and where the run breaks

{{< figure src="/afsi/demo400-results.png" title="Figure 2. A short run at $64 \times 32$ for 400 steps with the turtle outline overlaid, and the follower-pressure waveform applied." >}}

{{< figure src="/afsi/demo400-turtle-1s.png" title="Figure 3. The run at $t = 0, 0.1, 0.2, 0.35, 0.5, 0.75, 1$ s. Top: fluid velocity, which organises into four lobes around the flapping limbs. Bottom: pressure, which is a dipole across the body. The black outline is the deformed turtle mesh." >}}

{{< figure src="/afsi/demo400-history.png" title="Figure 4. The three diagnostics that matter. Left: the largest fluid velocity, on a log scale — it tracks the pressure ramp up to $t \approx 0.4$ s and then runs away to 28 m/s. Middle: the limb deflection (±0.6 m). Right: the applied follower pressure." >}}

<p class="tcaption">Table 2. The run to $t \le 1$ s.</p>

| Quantity | Value |
|---|---|
| Load | follower pressure on the limb edges, fast-open waveform of period 2 s, peak 100 at $t = 0.2$ s |
| Inlet | **zero for the whole run** — the inlet condition is never imposed and the prescribed amplitude is zero, so every motion in the fluid comes from the deforming body |
| Fluid velocity | $1.2\,\mathrm{m\,s^{-1}}$ at $t = 0.35$ s, $28\,\mathrm{m\,s^{-1}}$ at $t = 1$ s |
| Limb deflection | $+0.60 / -0.60\,\mathrm{m}$ in $y$, against a body height of $33.8$ |
| Volume | $319.93 \to 319.78$, i.e. $0.05\,\%$ compression |

**The first four snapshots are usable; the rest are not.** Up to $t \approx 0.4$ s
the response is physical and worth looking at: the pressure dipole across the
body, the four-lobe velocity pattern around the limbs, and the limbs deflecting by
about $1.8\,\%$ of the body height. Beyond that the solver runs away — by
$t = 1$ s the fluid reaches $28\,\mathrm{m\,s^{-1}}$ while the limb tips move at
only $\approx 10^{-3}\,\mathrm{m\,s^{-1}}$, a factor of $10^{4}$ larger than the
kinematics can explain. That is the explicit IB-FE coupling losing stability, not a
physical result, and it happens well inside the first load period. Running the
documented $30\,\mathrm{s}$ will need a smaller $\Delta t$, sub-iterated coupling,
or both.

## 5. Discussion and limitations

{{< color "red" >}}TODO: the inlet is not enforced in the current configuration —
decide whether the case should carry an axial inflow (as originally documented)
or remain a purely traction-driven problem.{{< /color >}}

* The coupling diverges inside the first load period (§4.4); the documented
  $600\,000$-step run is out of reach without a smaller $\Delta t$ or sub-iterated
  coupling.
* The logged "force norm" is $\int \mathbf{X}\cdot\mathbf{X}\,\mathrm{d}x$ over the
  solid coordinates, not a force norm.
* The follower-pressure direction is recomputed from the limb-edge centroids every
  step, so rigid-body motion of the outline rotates the load with it; whether that
  is intended should be confirmed.

## References

{{< color "red" >}}TODO: references — none cited; the follower-load benchmark
motivation should be cited if one exists.{{< /color >}}
