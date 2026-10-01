---
title: "343: Discs Through an Ideal 2-D Valve"
description: "Two compliant discs carried through an ideal 2-D valve."
date: 2026-09-12
weight: 343
academic: true
demo_id: demo_343
category: Application
dimension: 2D
solid_model: "FRH leaflets (upper C0, lower 10·C0) + two compliant discs at 0.01·C0"
coupling: "immersed boundary (`IBMesh`)"
reference: "— (disc force switched on against switched off)"
status: Partial
---

## 1. Introduction

The ideal-valve channel of [demo_340](/afsi/demo_340/) is re-used with two
compliant discs placed upstream. The upper and lower leaflets deliberately have
different stiffness (the lower one is ten times stiffer, as a stand-in for a
hardened leaflet), and a switch produces a control run in which the discs'
restoring force is dropped. The centre-line $u_x$ profiles at $y = 0.5$ and
$y = 1.1$ are compared between the two runs.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo343-setup.png" title="Figure 1. The ideal-valve geometry with the two compliant discs." >}}

The channel, the two FRH leaflets and the pulsatile inlet are those of
[demo_340](/afsi/demo_340/); the discs of radius $0.2$ sit at $(0.5, 0.5)$ and
$(0.5, 1.1)$ upstream of the valve.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the FRH leaflet constitution (as in demo_340), the disc stiffness law, and the IB coupling terms (see the symbol table page).{{< /color >}}

The discs use a stiffness of $0.01 \times$ the upper leaflet's $\mathbf P$; the
leaflets are the same FRH material as demo_340, with the lower leaflet ten times
stiffer.

### 2.3 Boundary and initial conditions

The inlet carries the pulsatile profile shared with demo_340
($5(\sin 2\pi t + 1.1)\,y\,(1.61-y)$), the channel walls are no-slip and the
outlet is at $p = 0$; the leaflets are clamped on their wall-attached edges.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. The geometry and the inlet profile are shared with demo_340.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $8.0 \times 1.61$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Leaflets | — | $0.0212 \times 0.7$ at $x \approx 1.9894$, clamped wall edges |
| Discs | `Circle1`, `Circle2` | radius $0.2$ at $(0.5, 0.5)$ and $(0.5, 1.1)$ |
| Leaflet material | `FRHMaterial` | `C0` $= 2\times10^{5}$ (upper), `C0_down` $= 10\,C0$ (lower), `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Disc stiffness | — | $0.01 \times$ the upper leaflet's $\mathbf{P}$ |
| Penalty | `beta` | $5\times10^{7}$ |

{{< color "red" >}}TODO: dimensionless numbers if the case is to be reported dimensionless.{{< /color >}}

## 3. Numerical setup

The fluid grid is $320 \times 64$ (cell $0.025 \times 0.0252$) with a Chorin
projection solver ($\mathrm{P2}$ / $\mathrm{P1}$) and
$\Delta t = 1/64000\,\mathrm{s}$ to $T = 3\,\mathrm{s}$ ($192\,000$ steps). The
time step was reduced to $1/64000$ specifically for this fine grid and large inlet
velocity, to prevent a transient flip of the lower leaflet root; the bulk modulus
was lowered from $4\times10^{6}$ to $4\times10^{5}$ because the larger value gave
excessively large FSI forces. The disc force is switched with a single flag, which
also selects the two result sets.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the valve opening (leaflet-tip separation and bend
from $t \approx 40$ ms), the disc transport downstream, the solid displacement
$\max\vert u_s\vert$ (discs against leaflets), the fluid energy norm $u_{L2}$ and
field maximum $\max\vert u\vert$, and the centre-line $u_x$ profiles at the two
disc heights with and without the disc force.

### 4.2 Comparison with reference

{{< color "red" >}}TODO: quantify the disc-force-on vs disc-force-off centre-line
comparison — the control run is meant to isolate the discs' constitutive force, but
no numbers exist yet, and what the control actually removes is itself in doubt (see
§5).{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Centreline $u_x$ (at disc heights) |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — a single resolution was
used; no refinement study exists.{{< /color >}}

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo343-valve-discs.png" title="Figure 2. The run: velocity magnitude with the solids shaded by their own displacement (top: whole channel, bottom: the valve region). The leaflets swing open as the inlet rises, forming an asymmetric nozzle, while the two discs are carried downstream." >}}

{{< figure src="/afsi/demo343-displacement.png" title="Figure 3. Solid displacement over the run. The maximum grows steadily with the pressure load; the discs are 100x softer than the leaflets, so they dominate it." >}}

<p class="tcaption">Table 2. The run to $t \le 0.2$ s.</p>

| Quantity | Value |
|---|---|
| $u_{L2}$ | grows monotonically $73 \to 297$ (the inlet forcing is still ramping up to its $t = 0.25$ s peak) |
| Field | $\max\lvert u\rvert = 8.05\,\mathrm{m\,s^{-1}}$ |
| Solid $\max\lvert u_s\rvert$ | $0.824\,\mathrm{m}$ — carried by the soft discs, not the leaflets |
| Leaflet opening | the two tips separate and bend downstream from $t \approx 40$ ms, reaching a nozzle-like shape by $t = 200$ ms |

{{< figure src="/afsi/demo343-results.png" title="Figure 4. The centreline at the two disc heights after 500 steps, with and without the disc force. The two runs differ only near the discs, which is what the control was meant to expose — it removes the constitutive force but leaves the markers coupled." >}}

## 5. Discussion and limitations

* The control run does not remove the discs: it only omits their constitutive
  force. The markers stay in the coupled system, still receive the interpolated
  fluid velocity and are still spread back into the fluid, so what the control
  actually measures is unclear.
* The leaflet stiffness ratio (lower leaflet ten times stiffer) is a modelling
  choice standing in for a hardened leaflet; its physical basis is not documented.

## References

{{< color "red" >}}TODO: references — none cited; the hardened-leaflet setup
suggests a clinical motivation that should be cited.{{< /color >}}
