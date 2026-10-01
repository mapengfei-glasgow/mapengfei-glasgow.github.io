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
coupling: "multi-direct forcing (own AB2 fractional step)"
reference: "DFIBMFoam — CircularFishSwimming (FEniCSx port)"
status: Partial
---

## 1. Introduction

A fish body with a NACA thickness distribution and a travelling-wave midline swims
around a prescribed circle inside a closed tank. Where the fixed-cylinder case of
[demo_339](/afsi/demo_339/) prescribes zero marker velocity, here the desired
velocity is the swimming kinematics itself,
$\mathbf{U}^d = (\mathbf{X}(t) - \mathbf{X}(t-\Delta t))/\Delta t$, fed into a
multi-direct-forcing loop. The solver is not the standard projection solver: the
case carries its own AB2 / semi-implicit fractional-step scheme.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo421-setup.png" title="Figure 1. The closed tank, the prescribed circular path, and the travelling-wave midline of the body." >}}

The tank is $1.4 \times 1.4\,\mathrm{m}$ and **must start at the origin** (see
§5). The fish is $0.1\,\mathrm{m}$ long and follows a circle of radius
$0.3\,\mathrm{m}$ centred at $(0.7, 0.7)$, i.e. the tank centre, with a cycle
period of $37.7\,\mathrm{s}$.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the
multi-direct-forcing formulation, and the kinematic constraint that imposes the
swimming motion (see the symbol table page).{{< /color >}}

The prescribed kinematics are: a travelling-wave midline (wavelength
$0.1\,\mathrm{m}$, period $0.5\,\mathrm{s}$), a circular orbit, and desired marker
velocities $\mathbf{U}^d = (\mathbf{X}(t)-\mathbf{X}(t-\Delta t))/\Delta t$.

### 2.3 Boundary and initial conditions

No-slip on all four walls of the closed tank, with one pressure degree of freedom
pinned at the corner; the body is driven by the marker forcing. The tank starts
from rest.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters (SI units). The tank must start at the origin — see §5.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Tank | `Lx`, `Ly` | $1.4 \times 1.4\,\mathrm{m}$, origin $(0,0)$ (required) |
| Density / viscosity | `rho`, `mu` | $1000\,\mathrm{kg\,m^{-3}}$ / $0.01\,\mathrm{Pa\,s}$ |
| Fish length | `fish_length` | $0.1\,\mathrm{m}$ |
| Undulation | `wavelength`, `wave_period` | $0.1\,\mathrm{m}$ / $0.5\,\mathrm{s}$ |
| Orbit | `orbit_radius`, `cycle_period`, `orbit_center` | $0.3\,\mathrm{m}$ / $37.7\,\mathrm{s}$ / $(0.7, 0.7)$ |
| Markers | `n_sections` | $120$ sections → $240$ surface markers ($\Delta s = 0.83\,\mathrm{mm}$) |

{{< color "red" >}}TODO: define the Reynolds number actually realised by the
undulation kinematics (the value the page used to print was based on a hard-coded
speed).{{< /color >}}

## 3. Numerical setup

The fluid grid is $280 \times 280$ ($h = 0.005\,\mathrm{m}$), the time step
$\Delta t = 0.001\,\mathrm{s}$ for $T = 1.0\,\mathrm{s}$ ($1000$ steps,
$\approx 2$ undulation periods), with $n_{iter} = 5$ direct-forcing iterations per
step.

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

{{< color "red" >}}TODO: grid and time-step sensitivity — the run used a lowered
resolution ($N = 140$); no paired refinement exists.{{< /color >}}

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo421-results.png" title="Figure 2. Marker positions over the run, and the prescribed circular path." >}}

The fields and the body trace were generated for the figures below, at
$N_x = N_y = 140$ and $1000$ steps of $\Delta t = 0.001$.

{{< figure src="/afsi/demo421-fish-1s.png" title="Figure 3. The tank at $t = 0, 0.2, 0.4, 0.6, 0.8, 1$ s (top) with the fish silhouette from the traced outline, and a near-body zoom (bottom). Each undulation cycle leaves a pair of counter-rotating eddies behind the body; the tank itself reacts with a slow return flow, which is what makes this a closed-domain case rather than a towed-fish one." >}}

{{< figure src="/afsi/demo421-path.png" title="Figure 4. Body-centroid path over the run and the net displacement. The tank is 14 body lengths across and one orbit is prescribed to take 37.7 s, so 1 s covers only 2.7 % of the circle." >}}

{{< figure src="/afsi/demo421-pyvista.png" title="Figure 5. The same instant rendered on the whole tank and in a near-body zoom, from the same mesh." >}}

<p class="tcaption">Table 2. The run at $N = 140$, $t \le 1$ s.</p>

| Quantity | Value |
|---|---|
| Coverage | $1000$ steps at $\Delta t = 0.001$ ($t \le 1$ s, two undulation periods) |
| Net body travel | $0.0503\,\mathrm{m}$ = $0.50$ body lengths (mostly in $y$) |
| $\max\lvert u\rvert$ in the tank | $0.19\,\mathrm{m\,s^{-1}}$, against a body length of $0.1\,\mathrm{m}$ and an undulation period of $0.5\,\mathrm{s}$ |
| Body length / marker count | $0.0992\,\mathrm{m}$ from the traced outline, 240 markers |

The striking feature is how **local** the flow is: the fish is $7\,\%$ of the tank
across, so almost all of the kinetic energy sits within a body length of the
surface and the tank-scale motion is a slow return flow. Filling the prescribed
$37.7\,\mathrm{s}$ orbit would need roughly forty times the steps.

## 5. Discussion and limitations

* **Domain-origin constraint.** The coupling assumes the tank starts at the
  origin: the kernel computes grid indices as $X/\Delta h$ without subtracting the
  domain origin while the mesh lookup uses $(x - x_0)/\Delta x$, so a non-origin
  domain shifts the coupling by $x_0/\Delta x$ cells. The workaround used here is
  to keep the tank at the origin and move the orbit centre to the tank centre.
* **The force integral does not converge.** Marker volumes are
  $\Delta V_l = \Delta s_l h \propto h$, so
  $\int \mathbf{f}_{\mathrm{IBM}}\,\mathrm{d}V$ shrinks with refinement and the
  printed thrust/lateral forces are magnitude references only.
* The body counts on all $240$ markers receiving a force every iteration; the
  marker force accumulates in Python because the spreading itself overwrites
  rather than accumulates — without the accumulation only the last iteration's
  force survives and the flow is barely driven.
* The prescribed orbit period (37.7 s) is long compared with the covered window
  (1 s), so only 2.7 % of the circle is exercised.

## References

{{< color "red" >}}TODO: references — add the DFIBMFoam / CircularFishSwimming
source the port is based on.{{< /color >}}
