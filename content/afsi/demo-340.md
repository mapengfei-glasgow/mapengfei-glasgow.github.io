---
title: "340: Ideal 2-D Valve with Fibre-Reinforced Leaflets"
description: "Two fibre-reinforced leaflets in a pulsatile channel, compared against published reference curves."
date: 2026-09-12
weight: 340
academic: true
demo_id: demo_340
category: Benchmark
dimension: 2D
solid_model: "fibre-reinforced hyperelastic (FRH) leaflets, exponential fibre term"
coupling: "immersed boundary (Chorin fluid, massless kinematic solid)"
reference: "Ryan et al. M2/M3; Kamensky et al."
status: Verified
---

## 1. Introduction

Two thin leaflets sit in a straight channel driven by a pulsatile inlet profile;
they are fibre-reinforced hyperelastic (FRH) solids coupled to the fluid through
the immersed boundary. The case has two axes: a comparison of the tip displacement
against published reference curves (Ryan et al. M2/M3, Kamensky et al.), and a
fibre-angle study at $45^\circ$, $60^\circ$ and $75^\circ$.

{{< figure src="/afsi/demo340-setup.png" title="Figure 1. The channel and the two fibre-reinforced leaflets, with the pulsatile inlet and the clamped edges." >}}

## 2. Problem description

### 2.1 Geometry

A straight channel $\Omega_f = [0,8]\times[0,1.61]$ carries the fluid. Two thin
fibre-reinforced hyperelastic leaflets hang from the channel walls and move with
the flow:

$$
\Omega_f = [0,8]\times[0,1.61], \qquad
\Omega_s = \Omega_1 \cup \Omega_2, \qquad
\Omega_1 = [1.9788,2.0]\times[0,0.7], \quad
\Omega_2 = [1.9788,2.0]\times[0.91,1.61].
$$

{{< color "red" >}}TODO: figure placeholder — dimensioned leaflet geometry, if a detail sketch is needed next to Figure 1.{{< /color >}}

### 2.2 Governing equations

The fluid satisfies

$$
\rho\left(\frac{\partial \mathbf u}{\partial t}
+ (\mathbf u\cdot\nabla)\mathbf u\right) = -\nabla p + \mu\nabla^2\mathbf u
+ \mathbf f_{\mathrm{IB}},
\qquad \nabla\cdot\mathbf u = 0
$$

with $\rho = 1$, $\mu = 0.1$, and $\mathbf f_{\mathrm{IB}}$ the immersed-boundary
force that communicates the leaflets to the fluid.

The leaflets are FRH solids. With $\mathbf F = \nabla_{\!X}\mathbf X$ the
deformation gradient, $J = \det\mathbf F$ and the isochoric right Cauchy–Green
tensor $\bar{\mathbf C} = J^{-2/3}\mathbf F^{\mathsf T}\mathbf F$, the strain-energy
density is

$$
\Psi = \frac{C_0}{2}\bigl(\bar I_1 - 3\bigr)
+ C_1\bigl(e^{\bar I_4 - 1} - \bar I_4\bigr)
+ \frac{\kappa}{4}\bigl(J^2 - 1\bigr) - \frac{\kappa}{2}\ln J,
$$

where $\bar I_1 = \operatorname{tr}\bar{\mathbf C}$,
$\bar I_4 = \mathbf f_1\cdot\bar{\mathbf C}\mathbf f_1$, and $\mathbf f_1$ is the unit
fibre direction. The parameters are the shear modulus $C_0 = 2\times10^5$, the fibre
stiffness $C_1 = 1\times10^6$ and the bulk modulus $\kappa = 4\times10^5$. The
exponential fibre term is what makes the leaflets nearly inextensible along
$\mathbf f_1$: a $45^\circ$ layup for each leaflet, mirrored between the two so the
pair opens symmetrically. The first Piola–Kirchhoff stress is the derivative
$\mathbf P = \partial\Psi/\partial\mathbf F$.

The solid is advanced by a weak statement of the internal force only — there is no
solid mass term:

$$
\int_{\Omega_s}\mathbf P(\mathbf F):\nabla_{\!X}\delta\mathbf v\,\mathrm dX
\;+\;\beta\sum_{e\in\{4,15\}}\int_{\Gamma_e}
\bigl(\mathbf X - \mathbf X_0\bigr)\cdot\delta\mathbf v\,\mathrm ds
\;=\;0 ,
$$

where the second term is a penalty that pins the wall-attached leaflet edges
($\beta = 10^8$); $\mathbf X$ are the *current* solid node coordinates, so the
form is assembled from the Lagrangian coordinates themselves rather than from a
displacement field, and no separate displacement variable appears.

### 2.3 Boundary and initial conditions

On the inlet, $x = 0$,

$$
\mathbf u(0,y,t) = \bigl(5(\sin 2\pi t + 1.1)\,y\,(1.61-y),\;0\bigr),
$$

so the pulse has period $1\,\mathrm{s}$, and the peak of the profile oscillates
between $5\times0.1 = 0.5$ and $5\times2.1 = 10.5$ over each cycle (it peaks at
$t = 1/4\,\mathrm{s}$ and troughs at $t = 3/4\,\mathrm{s}$); the walls are no-slip
and the outlet carries $p = 0$. The channel starts from rest.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Channel, leaflets and material. The fluid grid and the leaflet mesh are fixed; the fibre angle is the only parameter that changes between runs.</p>

| Quantity | Symbol / code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $8.0 \times 1.61$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.1$ |
| Leaflets | `lx`, `ly` | $0.0212 \times 0.7$, at $x \approx 1.9894$, $y = 0$ and $y = 0.91$ |
| Clamped edges | `dss(4)`, `dss(15)` | wall-attached edges, penalty `beta` $= 1\times10^{8}$ |
| Material | `FRHMaterial` | `C0` $= 2\times10^{5}$, `C1` $= 1\times10^{6}$, `kappa` $= 4\times10^{5}$ |
| Fibre vectors | `f1_d`, `f1_u` | $45^\circ$: $(0.7071, \pm0.7071)$; the $60^\circ$ and $75^\circ$ layups differ only in this vector |

{{< color "red" >}}TODO: dimensionless numbers ($\mathrm{Re}$, solid-to-fluid
stiffness ratios) if the case is to be reported dimensionless.{{< /color >}}

## 3. Numerical setup

The fluid and the solid live on different meshes and are coupled only through
interpolation with a regularised delta function. Let $\{\mathbf X_l\}$ be the solid
nodes and $\{\mathbf x_{ij}\}$ the fluid grid nodes. Each time step does four
things.

**1. Advance the fluid one step without the solid.** A Chorin projection step: a
tentative velocity, a pressure Poisson solve with $p = 0$ on the outlet, then an
$L^2$ projection back onto the divergence-free space with the boundary conditions
re-imposed.

**2. Interpolate the fluid velocity onto the solid nodes**,

$$
\mathbf U_l = \sum_{ij} \delta_h(\mathbf x_{ij} - \mathbf X_l)\,\mathbf u_{ij}.
$$

**3. Advect the solid nodes** with that velocity,

$$
\mathbf X^{\,n+1}_l = \mathbf X^{\,n}_l + \Delta t\,\mathbf U_l .
$$

This is the defining choice of the case: the leaflets are **massless** and purely
kinematic. They move exactly as the fluid at their location moves, and their
elasticity enters only through the force they push back in step 4 — the same
formulation as the standard immersed-boundary method for elastic boundaries.

**4. Spread the elastic force back onto the fluid**,

$$
\mathbf f_{ij} = \sum_l \delta_h(\mathbf x_{ij} - \mathbf X_l)\,
\mathbf F_l , \qquad
\mathbf F_l = -\int_{\Omega_s}\mathbf P(\mathbf F):\nabla_{\!X}\delta\mathbf v_l\,\mathrm{d}X
- \beta\,(\mathbf X_l - \mathbf X_{0,l})\big|_{\Gamma_4\cup\Gamma_{15}} .
$$

Because step 1 already used $\mathbf f^n_{\mathrm{IB}}$ when it advanced the fluid,
the coupled scheme is explicit in time: fluid, then solid, then force, then next
step.

<p class="tcaption">Table 2. Numerical setup.</p>

| Quantity | Value |
|---|---|
| Fluid grid | $128 \times 32$ (cell $0.0625 \times 0.0503$) |
| Solid mesh size | $0.01$ |
| Time step / end time | $1/16000$ / $3.0$ ($48\,000$ steps) |
| Solver | Chorin, $\mathrm{P2}$ velocity, $\mathrm{P1}$ pressure, force $\mathrm{P2}$ |

## 4. Results

### 4.1 Quantities of interest

The quantity the case is built around is the **leaflet-tip displacement** as a
function of time at the free tips (both components), compared against the
published reference curves and across fibre angles. Secondary quantities are the
whole-leaflet $\max\vert u_s\vert$, the opening of the free gap between the tips,
the peak velocity in the field, and the run-to-run agreement measures (maximum
difference against the archived series, cycle-to-cycle repeat).

### 4.2 Comparison with published results

{{< figure src="/afsi/demo340-results.png" title="Figure 2. Archived probe series for the three fibre angles, against the digitised literature curves." >}}

The archived probe series ends at $t = 2.9999\,\mathrm{s}$:

<p class="tcaption">Table 3. Leaflet-tip displacement at the end of the run, against the published reference curves (all values in mesh units, endpoint of each series).</p>

| Source | $x$ displacement | $y$ displacement |
|---|---|---|
| AFSI, $45^\circ$ fibres | $0.5141$ | $0.2624$ |
| AFSI, $60^\circ$ fibres | $0.5099$ | $0.2587$ |
| AFSI, $75^\circ$ fibres | $0.4945$ | $0.2403$ |
| Ryan et al. M2 | $0.4614$ | $0.2083$ |
| Ryan et al. M3 | $0.4759$ | $0.2229$ |
| Kamensky et al. | $0.4753$ | $0.2228$ |

The angle trend is the expected one — the stiffer $75^\circ$ layup deflects least —
but all three AFSI runs sit above the reference band ($+8\,\%$ in $x$, up to
$+18\,\%$ in $y$ for $45^\circ$). That offset is systematic, not scatter, and it
is worth carrying when reading any comparison figure here.

{{< color "red" >}}TODO: the mapping from archived column to fibre angle is
unverified — the series headers are run ids, and the $45^\circ/60^\circ/75^\circ$
ordering lives only in a comment.{{< /color >}}

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — the archived runs used a
single resolution ($128 \times 32$, $\Delta t = 1/16\,000$) and no refinement
study was performed.{{< /color >}}

### 4.4 Flow and deformation fields

A full $T = 3$ s run was made at the default resolution ($48\,000$ steps at
$\Delta t = 1/16\,000$), driven by the pulsatile inlet
$5(\sin 2\pi t + 1.1)\,y\,(L_y - y)$.

{{< figure src="/afsi/demo340-valve-3s.png" title="Figure 3. The run at 0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 2 and 3 s. Top: the whole 8 x 1.61 channel (dashed box = the zoom below). Middle: the valve region with streamlines — the leaflets are shaded by their own displacement. Bottom: the two leaflets alone, dotted lines marking the undeformed positions. The leaflets are pushed downstream as the inlet rises and spring back as it falls." >}}

{{< figure src="/afsi/demo340-history.png" title="Figure 4. Leaflet-tip displacement against the published curves: Ryan et al. M2/M3, Kamensky et al., the archived AFSI 45-degree series (thick grey) and this run (thin red), plus the inlet waveform with the snapshot times marked. This run is indistinguishable from the archive at this scale." >}}

<p class="tcaption">Table 4. This run ($45^\circ$, $T = 3$ s) against the archived AFSI series and the reference curves.</p>

| Quantity | Value |
|---|---|
| Resolution / steps | $128 \times 32$, $\Delta t = 1/16\,000$, $48\,000$ steps |
| Tip $x$-displacement | ranges $0.00015 \to 0.6015$; peak at $t \approx 1.25$ s |
| Tip $y$-displacement | ranges $0.000 \to 0.4476$; peak at $t \approx 1.25$ s |
| Whole-leaflet $\max \vert u_s \vert$ | $0.7515$ m, against a leaflet length of $0.7$ |
| Agreement with the archived AFSI $45^\circ$ series | $\max$ difference $3.7\times10^{-4}$ on a $0.6014$ signal (0.06 %) — the archived series is reproducible |
| Cycle-to-cycle repeat | $x$ at $t = 0.25$ s vs $t = 2.25$ s: $0.5942$ vs $0.6013$ (1.2 %), i.e. still creeping toward the periodic state |
| Versus the literature band | this run sits $\sim 8$ % above Ryan M2/M3 and Kamensky in $x$ and up to $\sim 18$ % in $y$ — the same offset the archived AFSI series shows |

The deflection is **quasi-steady**: the tip tracks the inlet waveform with no
visible phase lag, peaking as the inlet peaks ($t \approx 0.25$ s into each
cycle) and returning to a small residual as the inlet dips. The leaflets swing
apart rather than toward each other — the free gap between the tips widens from
$0.21$ (undeformed) up to $1.08$ at the peak, and narrows back to $0.50$ at the
trough, i.e. it stays between $31\,\%$ and $67\,\%$ of $L_y$. The highest speeds
in the field ($\sim 9.2$ m/s, against an inlet peak of $10.5$ m/s) sit at
$x \approx 2.7$, just downstream of the leaflets, rather than at the inlet.

## 5. Discussion and limitations

**Why the AFSI curves sit above the literature band** ($+8\,\%$ in $x$, up to
$+18\,\%$ in $y$) is an open question — the offset is systematic across the three
fibre angles and across the archived and re-run series.

{{< color "red" >}}TODO: discuss the cause of the offset against Ryan et al. /
Kamensky et al. — boundary-condition treatment, penalty choice, or the massless
kinematic leaflet model.{{< /color >}}

{{< color "red" >}}TODO: which archived series corresponds to which fibre angle —
confirm before using Figure 2 quantitatively.{{< /color >}}

## References

{{< color "red" >}}TODO: references — add Ryan et al. (M2/M3), Kamensky et al. and
the AFSI paper; the digitised curves in the repository are the data source for the
comparison.{{< /color >}}
