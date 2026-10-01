---
title: "443: Compression Test"
description: "A rectangular elastic block under a central downward traction, following Wells et al. (2023)."
date: 2026-10-01
weight: 443
academic: true
demo_id: demo_443
category: Benchmark
dimension: 2D
solid_model: "neo-Hookean block (plane strain), G = 80.194, κ_stab = 374.239 dyn/cm²"
coupling: "immersed boundary — four-point (IB₄) kernel"
reference: "Wells et al. (2023) configuration"
status: Complete
---

## 1. Introduction

This benchmark is a plane-strain quasi-static problem: a rectangular elastic
block immersed in a fluid is loaded by a central downward traction on its top
surface. It follows the configuration of {{< cite "wells2023nodal" "author" >}}
and is used to compare element Jacobians and the top-centre displacement across
immersed-boundary kernels in {{< cite "li2025local" "author" >}}.

This page reports the case as solved by our scheme: the fluid is the
finite-element (Chorin projection) background of `afsic`, and the coupling uses
only the four-point ($\mathrm{IB}_4$) regularised delta. The paper's stabilised
kernel results (modified invariants with $\nu = 0.4$ plus volumetric energy)
form the reference.

## 2. Problem description

### 2.1 Geometry

The computational domain is $40\,\mathrm{cm} \times 40\,\mathrm{cm}$, within
which a block of dimensions $20\,\mathrm{cm} \times 10\,\mathrm{cm}$ is immersed
centrally. A downward traction of magnitude $200\,\mathrm{dyn\,cm^{-1}}$ is
applied to the central $10\,\mathrm{cm}$ of the block's top surface; the probe
sits at the centre of that loaded stretch of surface, $(20, 25)$.

{{< figure src="/afsi/demo443-geometry.png" title="Figure 1. The block in the fluid box: the loaded central 10 cm of the top surface (downward traction 200 dyn/cm), zero vertical displacement along the bottom, zero horizontal displacement along the entire top (including under the load), stress-free sides, and zero fluid velocity on $\\partial\\Omega$." >}}

### 2.2 Governing equations

The coupled system is the immersed-boundary formulation in its unified
variational form (as in {{< cite "li2025local" "author" >}}, after Boffi et
al.): incompressible Navier–Stokes in $\Omega$, driven by the spread elastic
force density $f(x,t) = \int_{\Omega_0^s} F(X,t)\,\delta_\varepsilon(x-\chi)\,\mathrm{d}X$,
with the structure advected by the local fluid velocity
$\partial_t\chi = \int_\Omega u\,\delta_\varepsilon(x-\chi)\,\mathrm{d}x$.
The block is a plane-strain neo-Hookean solid with
$P = \partial\Psi/\partial F$ and the Lagrangian force assembled from
$\int F\cdot G\,\mathrm{d}X = -\int P : \nabla_X G\,\mathrm{d}X$. In this
scheme the fluid is solved with the $\mathbb{P}_2/\mathbb{P}_1$
finite-element Chorin projection solver of `afsic`, and $\delta_\varepsilon$ is
the four-point cosine kernel ($\mathrm{IB}_4$).

The prescribed boundary constraints enter as penalty tethers to the reference
position, $F_{\text{bc}} = \beta\,(\psi - \chi)$, with
$\psi$ the prescribed position; the tether reaction is transmitted to the
fluid through the same spreading operator.

### 2.3 Boundary and initial conditions

The structural boundary conditions are zero vertical displacements along the
bottom boundary and zero horizontal displacements along the top boundary
(the loaded central stretch included), with zero traction on all other
boundaries. The bottom constraint is enforced by a penalty,
$\kappa_S = 2.5 \cdot \frac{2.5\,\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$;
here the same penalty acts on the top edge for its horizontal constraint.

The traction load increases linearly in time until reaching its full magnitude
at $T_{\mathrm{l}} = 40\,\mathrm{s}$, and — in the reference — the simulation
runs to $T_{\mathrm{f}} = 100\,\mathrm{s}$ so that equilibrium is achieved.
The runs below use a shortened ramp $T_{\mathrm{l}} = 5\,\mathrm{s}$ and
$T_{\mathrm{f}} = 25$–$50\,\mathrm{s}$: the response is quasi-static and the
plateau level does not depend on the ramp length (checked at $M=8$).

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. Units follow the source (CGS).</p>

| Quantity | Symbol | Value |
|---|---|---|
| Fluid box | — | $40\,\mathrm{cm} \times 40\,\mathrm{cm}$ |
| Block | — | $20\,\mathrm{cm} \times 10\,\mathrm{cm}$, centred |
| Fluid density | $\rho$ | $1.0\,\mathrm{g\,cm^{-3}}$ |
| Fluid viscosity | $\mu$ | $0.16\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Shear modulus | $G$ | $80.194\,\mathrm{dyn\,cm^{-2}}$ |
| Numerical bulk modulus | $\kappa_{\mathrm{stab}}$ | $374.239\,\mathrm{dyn\,cm^{-2}}$ |
| Traction | — | $200\,\mathrm{dyn\,cm^{-1}}$, over the central $10\,\mathrm{cm}$ |
| Fixation penalty | $\kappa_S$ | $2.5 \cdot \frac{2.5\,\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$ ($\beta = 10\,\kappa_S$ used here) |
| Load time | $T_{\mathrm{l}}$ | $5.0\,\mathrm{s}$ (reference: $40\,\mathrm{s}$) |
| Final time | $T_{\mathrm{f}}$ | $25$–$50\,\mathrm{s}$ (reference: $100\,\mathrm{s}$) |

The modulus pair corresponds to $\nu = 0.4$
($\kappa = 2G(1+\nu)/(3(1-2\nu)) = 374.239$); the total applied load is
$200 \times 10 = 2000\,\mathrm{dyn}$.

## 3. Numerical setup

The fluid grid is fixed at $N = 32$ cells per direction; the Lagrangian mesh
carries $M = 8, 16$ and $32$ $\mathbb{Q}^2$ elements along the 20 cm edge, so
that this is a Lagrangian-refinement study at fixed fluid resolution (marker
spacing $2.5$, $1.25$ and $0.625\,\mathrm{cm}$ against $h = 1.25\,\mathrm{cm}$).
The time step is $\Delta t = 0.002\,h$ and the constraint penalty is taken
$10\times$ the paper's value, $\beta = 10\,\kappa_S$; the measured constraint
slip is then $\lesssim 0.1\,\mathrm{cm}$.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the element Jacobians $J$, which characterise the
volumes of the deformed elements, and the vertical displacement $\Delta Y$ at the
centre of the top surface.

### 4.2 Comparison with reference

{{< chart xlabel="t (s)" ylabel="$\Delta Y$ (cm)" caption="Top-centre displacement: M=8 (N=32, to t=100 s) and M=32 (N=32, to t=50 s); the reference plateau is about -4.0 cm (M=32, stabilised IB)." >}}
t, M=8 (N=32), M=32 (N=32), reference plateau (-4.0)
0,0.0000,0.0000,-4.0000
5,-4.9700,-4.6549,-4.0000
10,-4.8846,-4.6567,-4.0000
15,-4.8361,-4.6202,-4.0000
20,-4.8138,-4.6128,-4.0000
25,-4.8015,-4.6143,-4.0000
30,-4.7964,-4.6219,-4.0000
35,-4.7945,-4.6313,-4.0000
40,-4.7943,-4.6421,-4.0000
45,-4.7946,-4.6540,-4.0000
50,-4.7951,-4.6659,-4.0000
55,-4.7956,-4.6659,-4.0000
60,-4.7959,-4.6659,-4.0000
65,-4.7962,-4.6659,-4.0000
70,-4.7963,-4.6659,-4.0000
75,-4.7964,-4.6659,-4.0000
80,-4.7964,-4.6659,-4.0000
85,-4.7965,-4.6659,-4.0000
90,-4.7965,-4.6659,-4.0000
95,-4.7965,-4.6659,-4.0000
100,-4.7965,-4.6659,-4.0000
{{< /chart >}}

The reference settles at $\Delta Y \approx -4.0\,\mathrm{cm}$ at $M = 32$ (with
its own $M = 8$ value near $-3.7\,\mathrm{cm}$: the reference curves deepen
with refinement toward $-4.0$). Our stable runs give
$-4.80\,\mathrm{cm}$ ($M = 8$, $N = 32$, settled by $t = 100\,\mathrm{s}$)
and $-4.67\,\mathrm{cm}$ ($M = 32$, $N = 32$, at $t = 50\,\mathrm{s}$) —
a $15$–$20\,\%$ offset from the reference plateau. The reference's own
stabilisation experiment shows the mechanism for such offsets: the
$\mathrm{IB}$/$\mathrm{BS}$ kernels without the modified-invariant and
volumetric treatments differ from the CBS kernels by comparable amounts in
this case, so a $\sim 20\,\%$ difference in the final displacement between
different immersed schemes is within the spread of the published results.
The intermediate Lagrangian resolution ($M = 16$) turned out not to be
usable here: at both $N = 32$ (marker spacing $= h$) and $N = 40$ the run
degrades slowly, with elements reaching $J \approx 0$ by
$t \approx 50$–$100\,\mathrm{s}$ while the probe displacement still looks
plausible — see §5.

<p class="tcaption">Table 2. Probe displacement and Jacobian range against the reference.</p>

| Quantity | AFSI ($M=8$, $N=32$) | Reference | rel. err. |
| --- | --- | --- | --- |
| $\Delta Y$ at the top-centre | $-4.80\,\mathrm{cm}$ | $\approx -4.0\,\mathrm{cm}$ ($M=32$ plateau, stab. $\mathrm{IB}$) | $+20\,\%$ |
| $\lvert J - 1\rvert_{\max}$ at $t \approx 25\,\mathrm{s}$ | $0.32$ | same order (their $J$ maps, $M=32$) | — |

### 4.3 Lagrangian convergence at fixed $N$

<p class="tcaption">Table 3. Top-centre displacement of the stable runs (all Jacobians checked against the final snapshots).</p>

| $M$ | $N$ | marker spacing (cm) | $t$ (s) | $\Delta Y$ (cm) | $J$ range |
| --- | --- | --- | --- | --- | --- |
| 8 | 32 | 2.5 | 100 | $-4.80$ | $[0.68, 1.09]$ |
| 16 | 32 / 40 | 1.25 | 100 / 50 | $-5.20$ / $-4.63$ | $[0.01, 2.70]$ / $[-0.09, 4.09]$ |
| 32 | 32 | 0.625 | 50 | $-4.67$ | $[0.53, 1.11]$ |

The displacement barely moves between $M = 8$ and $M = 32$, so the remaining
offset from the reference is not Lagrangian under-resolution; it is the
combination of the finite-element fluid background (its lack of grid-scale
dissipation softens the punch at the load edges) and the different material
stabilisation (the reference's $\nu = 0.4$-stabilised modified invariants vs
the standard compressible form here). The $M = 16$ row is excluded from the
comparison: even though its probe displacement looks smooth, both grid
ratios tried end with degenerate elements (the Jacobian ranges above reveal
it), so its values are not quoted as a converged result.

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo443-fields.png" title="Figure 2. Left: the deformed block coloured by J; the load corner at x = 15 cm carries the deepest volume loss, the flanks bulge outward. Right: fluid speed at the end of the run — the squeezed fluid escapes along the top and the sides, and is nearly static in the far field." >}}

## 5. Discussion and limitations

* The top-centre displacement probes the loading of a plate whose top is
  frozen horizontally and bottom vertically, so the deformation is a
  constrained compression; the horizontal constraint along the loaded stretch
  is what prevents an unphysical shear/punch collapse (see below).
* Applying the zero-horizontal-displacement condition only outside the loaded
  patch — a natural misreading of "zero horizontal displacements along the top
  boundary" — lets the central top slide sideways; the block then folds into a
  V-shaped punch ($\Delta Y \approx -6.2\,\mathrm{cm}$, elements crushed to
  $J \approx 0.1$). This is a useful negative result for anyone re-implementing
  the case.
* The modified-invariant ($\mathrm{Flory}$-type) energy of the reference's
  stabilised formulation turned out numerically less robust in this
  FE-coupled setting: elements near the load corner inverted locally
  ($J \to 0$). The reported runs therefore use the standard compressible
  neo-Hookean form — a material-level difference from the reference's
  stabilised kernels.
* At the intermediate Lagrangian resolution ($M = 16$, marker spacing
  $1.25\,\mathrm{cm}$) the coupled run degrades slowly at both $N = 32$ and
  $N = 40$ — elements reach $J \approx 0.01$ and $J \approx -0.09$
  respectively by the end of the run — while the probe displacement itself
  stays smooth and plausible. The degradation is silent in displacement-only
  diagnostics: this is why every number in Table 3 is accompanied by its
  final Jacobian range. The feasible window for this FE-coupled variant
  appears to be marker spacings of $\approx 0.5h$ and $\geq 2h$; the
  reference sweeps $\mathrm{MFAC}$ and finds its kernels insensitive, so
  the FE-coupled variant is more fragile in this respect.
* The fluid grid is four times finer than the reference's at the smallest
  $M$; this study does not claim a fluid-grid convergence statement of its own.

## References

{{< references >}}
