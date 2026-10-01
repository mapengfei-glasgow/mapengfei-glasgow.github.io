---
title: "441: Cook's Membrane"
description: "Cook's membrane — the classical plane-strain benchmark, in a modified 13 cm square domain."
date: 2026-10-01
weight: 441
academic: true
demo_id: demo_441
category: Benchmark
dimension: 2D
solid_model: "neo-Hookean block (plane strain), G = 83.333, κ_stab = 388.889 dyn/cm²"
coupling: "immersed boundary — four-point (IB₄) kernel"
reference: "Wells et al. (2023) configuration"
status: Complete
---

## 1. Introduction

Cook's membrane is a classical plane-strain benchmark for incompressible
elasticity: a block held on one side and loaded by a traction on the other, whose
corner displacement and element volumes probe an elasticity solver's robustness.
The configuration follows {{< cite "wells2023nodal" "author" >}}, with the
computational domain enlarged from the original
$10\,\mathrm{cm} \times 10\,\mathrm{cm}$ to
$13\,\mathrm{cm} \times 13\,\mathrm{cm}$ so that the grid resolution stays
integral during mesh-convergence studies.

This page reports the case as solved by our scheme: the fluid is the
finite-element (Chorin projection) background of `afsic`, and the coupling uses
only the four-point ($\mathrm{IB}_4$) regularised delta of
{{< cite "gruninger2024local" "author" >}}. The paper
{{< cite "li2025local" "author" >}} solves the same case with a
finite-difference fluid and compares the isotropic $\mathrm{IB}$ and
$\mathrm{BS}$ spreads against the divergence-free composite B-spline (CBS)
spreads; its computed plateau and Jacobian fields are used here as the
reference.

## 2. Problem description

### 2.1 Geometry

The computational domain is a $13\,\mathrm{cm} \times 13\,\mathrm{cm}$ square
filled with fluid, with the block immersed in it. The block's left side is held
fixed and its right side carries the load; the vertical displacement
$\Delta Y$ is monitored at the upper-right corner of the membrane, at
$(8.05\,\mathrm{cm},\, 9.5\,\mathrm{cm})$.

{{< figure src="/afsi/demo441-geometry.png" title="Figure 1. The trapezoidal membrane in the $13 \\times 13$ cm fluid box: the clamped left edge (length $4.4$ cm), the loaded right edge (length $1.6$ cm, upward traction $6.25$ dyn/cm), the probe at the upper-right corner, and zero fluid velocity on $\\partial\\Omega$." >}}

### 2.2 Governing equations

The coupled system is the immersed-boundary formulation in its unified
variational form ({{< cite "li2025local" "author" >}}, following Boffi et al.):
the incompressible Navier–Stokes equations in $\Omega$,
$\rho\left(\partial_t u + u\cdot\nabla u\right) = -\nabla p + \mu\nabla^2 u + f$,
$\nabla\cdot u = 0$, driven by the Lagrangian elastic force density
$F(X,t)$ of the immersed body, spread to the Eulerian grid as
$f(x,t) = \int_{\Omega_0^s} F(X,t)\,\delta_\varepsilon(x - \chi(X,t))\,\mathrm{d}X$,
with the structure advected by the local fluid velocity,
$\partial_t\chi = \int_\Omega u(x,t)\,\delta_\varepsilon(x - \chi)\,\mathrm{d}x$.
The solid is a plane-strain neo-Hookean material with first Piola–Kirchhoff
stress $P = \partial\Psi/\partial F$; the Lagrangian force follows from the
unified weak form
$\int F\cdot G\,\mathrm{d}X = -\int P : \nabla_X G\,\mathrm{d}X$
for all Lagrangian test functions $G$.

In this scheme the fluid is discretised with the finite-element (Taylor–Hood
$\mathbb{P}_2/\mathbb{P}_1$) Chorin projection solver of `afsic`, and the
regularised delta $\delta_\varepsilon$ is the four-point cosine kernel
($\mathrm{IB}_4$) with support spanning four Eulerian nodes. The paper's
comparison additionally employs the isotropic B-spline ($\mathrm{BS}$) and the
divergence-free composite B-spline (CBS) spreads on a finite-difference fluid
solver — those results are quoted in §4 as the reference.

### 2.3 Boundary and initial conditions

The left side of the block is fixed by a penalty,
$\kappa_S = 0.125\,\frac{\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$; an upward
traction of density $6.25\,\mathrm{dyn\,cm^{-1}}$ is applied to the right side;
all other structural boundaries are stress free, and the fluid is at rest with
zero velocity enforced on $\partial\Omega$. The traction ramps linearly in time,
reaching its full magnitude at $T_{\mathrm{l}} = 20\,\mathrm{s}$, and the
simulation runs to $T_{\mathrm{f}} = 50\,\mathrm{s}$ so that the configuration
settles. Because the coupling transmits the penalty reaction to the fluid, we
scale the fixation penalty by $10\times$ ($\beta = 10\,\kappa_S$): the measured
clamp slip then drops from $\approx 0.3\,\mathrm{cm}$ to
$\approx 0.05\,\mathrm{cm}$, a fairer realisation of the hard clamped edge used
in the reference.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Parameters. Units follow the source (CGS).</p>

| Quantity | Symbol | Value |
|---|---|---|
| Fluid density | $\rho$ | $1.0\,\mathrm{g\,cm^{-3}}$ |
| Fluid viscosity | $\mu$ | $0.16\,\mathrm{dyn\,s\,cm^{-2}}$ |
| Material model | — | neo-Hookean |
| Shear modulus | $G$ | $83.333\,\mathrm{dyn\,cm^{-2}}$ |
| Numerical bulk modulus | $\kappa_{\mathrm{stab}}$ | $388.889\,\mathrm{dyn\,cm^{-2}}$ |
| Traction density | — | $6.25\,\mathrm{dyn\,cm^{-1}}$, on the right side |
| Fixation penalty | $\kappa_S$ | $0.125\,\frac{\Delta x}{\Delta t}\,\mathrm{dyn\,cm^{-3}}$ ($\beta = 10\,\kappa_S$ used here) |
| Load time | $T_{\mathrm{l}}$ | $20.0\,\mathrm{s}$ |
| Final time | $T_{\mathrm{f}}$ | $50.0\,\mathrm{s}$ |

The modulus pair corresponds to Poisson ratio $\nu = 0.4$
($\kappa = 2G(1+\nu)/(3(1-2\nu)) = 388.889$), and the total load is
$6.25 \times 1.6 = 10\,\mathrm{dyn}$. As in demo_443, the reference's
effective response is incompressible — its discrete divergence-free coupling
holds $J$ within $[0.966, 1.010]$ — while our FE-coupled variant carries the
volume constraint in the material; the calibration check below quantifies what
that means for this case.

## 3. Numerical setup

The solid mesh uses $M = 8$ and $16$ $\mathbb{Q}^2$ elements per longest side
(the reference uses $\mathbb{Q}^1$ elements with the same $M$; the quadratic
elements are part of our solver), with $\mathrm{MFAC} = 1.0$, i.e.
$N = \left\lceil M \cdot \mathrm{MFAC} \cdot \frac{10}{6.5} \right\rceil = 13$
and $25$ fluid cells per direction, and a time step
$\Delta t = 0.002\,h$ (the penalty is re-scaled with $h/\Delta t$ so that all
penalty-to-inertia ratios match the paper's $\Delta t = 0.001\,\Delta x$). The
Eulerian grid is a uniform quadrilateral mesh, the velocity is
$\mathbb{P}_2$ and the pressure $\mathbb{P}_1$; the Lagrangian force density is
assembled from the unified weak form and spread with the $\mathrm{IB}_4$
kernel.

For reference, an economical protocol (load ramp shortened to
$T_{\mathrm{l}} = 2\,\mathrm{s}$) was tested at $M = 8$: it reproduces the
paper-protocol plateau (0.626 vs 0.625 cm). At $M = 16$ the shortened ramp
leaves the membrane ringing (the value is still $0.80\,\mathrm{cm}$ at
$t = 20\,\mathrm{s}$, relaxing toward the settled 0.655 cm), so the paper
protocol is used for all reported $M = 8, 16$ values.

A bulk-modulus calibration check ($\kappa \to 10\kappa$, the setting that
reproduces the reference's volume behaviour on demo_443) was also run at both
meshes with the paper protocol. Unlike the compression case, the two
calibrations bracket the reference: the raw constant leaves the volume looser
than the reference ($J$ down to $0.82$) and puts the corner displacement
inside the published band, while $10\kappa$ pins the volume to the
reference's range but raises the displacement above the band (Table 4).
Both results are reported; no unit conversion is hidden in this choice — all
quantities are in CGS and the two cases require opposite volume adjustments,
so a global factor (such as a Pa $\leftrightarrow$ dyn/cm² slip) cannot
explain them.

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the element Jacobians $J$, which characterise the
volumes of the deformed elements, and the vertical displacement $\Delta Y$ at the
membrane's upper-right corner.

### 4.2 Comparison with reference

The corner displacement history for the two meshes with the paper protocol:

{{< chart xlabel="t (s)" ylabel="$\\Delta Y$ (cm)" caption="Corner displacement history, paper protocol (TL=20 s, TF=50 s)." >}}
t, M=8 (N=13), M=16 (N=25), paper plateau (0.60-0.68, mid)
0,0.0000,0.0000,0.6400
2,-0.0866,-0.0376,0.6400
2.08,-0.0854,-0.0342,0.6400
4,-0.0564,0.0431,0.6400
4.16,-0.0475,0.0509,0.6400
6,0.0548,0.1688,0.6400
6.24,0.0696,0.1814,0.6400
8,0.1778,0.2612,0.6400
8.32,0.1928,0.2734,0.6400
10,0.2710,0.3238,0.6400
10.4,0.2842,0.3355,0.6400
12,0.3368,0.3886,0.6400
12.48,0.3515,0.4060,0.6400
14,0.3981,0.4689,0.6400
14.56,0.4175,0.4922,0.6400
16,0.4674,0.5450,0.6400
16.64,0.4907,0.5651,0.6400
18,0.5402,0.6003,0.6400
18.72,0.5642,0.6189,0.6400
20,0.6068,0.6545,0.6400
20.8,0.6230,0.6756,0.6400
22,0.6473,0.6951,0.6400
22.88,0.6454,0.6989,0.6400
24,0.6430,0.6917,0.6400
24.96,0.6319,0.6810,0.6400
26,0.6199,0.6702,0.6400
27.04,0.6139,0.6642,0.6400
28,0.6084,0.6634,0.6400
29.12,0.6105,0.6659,0.6400
30,0.6122,0.6690,0.6400
31.2,0.6162,0.6719,0.6400
32,0.6189,0.6720,0.6400
33.28,0.6202,0.6702,0.6400
34,0.6210,0.6683,0.6400
35.36,0.6202,0.6648,0.6400
36,0.6198,0.6637,0.6400
37.44,0.6192,0.6621,0.6400
38,0.6190,0.6620,0.6400
39.52,0.6198,0.6619,0.6400
40,0.6200,0.6618,0.6400
41.6,0.6213,0.6611,0.6400
42,0.6217,0.6608,0.6400
43.68,0.6228,0.6591,0.6400
44,0.6230,0.6588,0.6400
45.76,0.6237,0.6571,0.6400
46,0.6238,0.6570,0.6400
47.84,0.6245,0.6558,0.6400
48,0.6246,0.6557,0.6400
49.92,0.6254,0.6547,0.6400
50,0.6254,0.6546,0.6400
50,0.6254,0.6546,0.6400
{{< /chart >}}

The two meshes settle on close plateaus,
$\Delta Y = 0.625\,\mathrm{cm}$ ($M = 8$) and $0.655\,\mathrm{cm}$ ($M = 16$),
against the reference plateau band $0.59$–$0.68\,\mathrm{cm}$ computed at
$M = 32$ for the raw paper constants, i.e. before any bulk calibration: the
agreement is within $2.3\,\%$ of the band centre at $M = 16$. As the
calibration check in §4.3 shows, part of this agreement is a compensation of
two effects with opposite trends, so the comparison is quoted for both
calibrations there.

<p class="tcaption">Table 2. Probe displacement and Jacobian range against the reference (raw paper constants, $\kappa$).</p>

| Quantity | AFSI ($M=16$) | Reference | rel. err. |
| --- | --- | --- | --- |
| $\Delta Y$ at $(8.05, 9.5)\,\mathrm{cm}$ | $0.655\,\mathrm{cm}$ | $0.59$–$0.68\,\mathrm{cm}$ (band) | $+2.3\,\%$ vs band centre |
| $J$ range at $t = 50\,\mathrm{s}$ | $[0.821, 1.121]$ | $[0.966, 1.010]$ (stab. $\mathrm{IB}_3$, $M=32$) | ours looser |

The reference's stabilised Jacobian range is read from its $M = 32$ figure; the
$0.59$–$0.68\,\mathrm{cm}$ band spans its stabilised and unstabilised variants.

### 4.3 Convergence study

<p class="tcaption">Table 3. Corner displacement vs Lagrangian resolution (paper protocol, TL=20 s, TF=50 s).</p>

| $M$ | $N$ | $\Delta t$ (s) | $\Delta Y$ (cm) |
| --- | --- | --- | --- |
| 8 | 13 | 0.002 | 0.625 |
| 16 | 25 | 0.00104 | 0.655 |
| reference ($M = 32$) | — | 0.001 | $\approx 0.66$ plateau |

The displacement rises slowly with $M$ (0.625 → 0.655), approaching the
reference plateau from below. The reference resolves the same trend from the
other side: its own curves overshoot at small $M$ and settle onto
$\approx 0.66\,\mathrm{cm}$ by $M = 32$–$64$
({{< cite "li2025local" "author" >}}, their figure of $\Delta Y$ versus $M$ at
each $\mathrm{MFAC}$). A settled $M = 32$ run at the paper protocol requires
$\sim 10^5$ time steps in our solver; a shortened-ramp attempt at that
resolution was still relaxing when the run budget ended, so it is not quoted.
We did not re-run the full $\mathrm{MFAC}$ sweep; at $\mathrm{MFAC} = 1.0$ the
kernel support ($4h$, with markers every $h$) is commensurate with the membrane
edge resolution used in the reference.

<p class="tcaption">Table 4. Bulk-modulus calibration check (paper protocol, t = 50 s).</p>

| bulk | $M=8$: $\Delta Y$ / $J$ range | $M=16$: $\Delta Y$ / $J$ range |
| --- | --- | --- |
| $\kappa$ (raw) | $0.625\,\mathrm{cm}$ / $[0.833, 1.012]$ | $0.655\,\mathrm{cm}$ / $[0.821, 1.121]$ |
| $10\kappa$ | $0.745\,\mathrm{cm}$ / $[0.990, 1.025]$ | $0.750\,\mathrm{cm}$ / $[0.990, 1.020]$ |
| reference (stab., $M=32$) | $\approx 0.66\,\mathrm{cm}$ / $[0.966, 1.010]$ (both) | — |

The two effects move in opposite directions: the stiffer bulk pins the
volume to the reference's range and the displacement is mesh-converged
($0.745 \to 0.750$ from $M = 8$ to $16$), but it then overshoots the
reference band by $\approx 0.09\,\mathrm{cm}$; the raw bulk leaves the volume
looser than the reference yet its displacement sits inside the band. The
mechanism matching demo_443 — where the calibrated bulk *does* reconcile
everything — is therefore only half the story here: for the bending-dominated
Cook's membrane there remains a residual difference between the two schemes
at matched volume behaviour, most plausibly tied to the different Lagrangian
discretisations (our $\mathbb{Q}^2$ mesh and penalty clamp versus the
reference's $\mathbb{Q}^1$ mesh with its combined elastic + viscous tether).
We report the raw-constant result as the primary comparison and the calibrated
result as the volume-matched one, rather than selecting whichever number falls
inside the band.

### 4.4 Flow and deformation fields

{{< figure src="/afsi/demo441-fields.png" title="Figure 2. Left: fluid speed at the end of a fast-protocol run (M=16, N=25, t=20 s); the wake of the membrane motion is confined to the box. Right: the deformed membrane of that run coloured by the Jacobian J; the bending concentration along the clamped edge and near the loaded corner is visible." >}}

The settled $M = 16$ state (paper protocol, $t = 50\,\mathrm{s}$) holds
$J \in [0.821, 1.121]$ over the whole membrane — no element comes close to
degeneracy — with the largest volume error at the clamped edge, where the
bending enters the box. The fast-protocol snapshot of Figure 2 is caught
mid-ringing and is correspondingly closer to unity, $J \in [0.95, 1.04]$. The
fluid speed decays over the run and is $\mathcal{O}(10^{-2})$ at the end, two
orders below the peak mid-ramp velocity.

## 5. Discussion and limitations

* The scheme differs from the reference in the fluid solver (finite element
  $\mathbb{P}_2/\mathbb{P}_1$ Chorin rather than finite differences) and in the
  kernel set (only $\mathrm{IB}_4$). The comparison is therefore
  method-to-method rather than kernel-to-kernel; within that difference the
  converged probe displacement matches the published plateau to a few percent.
* The clamp is a penalty; its slip with $\beta = 10\,\kappa_S$ is
  $\approx 0.05\,\mathrm{cm}$, which contributes no more than
  $\mathcal{O}(0.05\,\mathrm{cm})$ to $\Delta Y$.
* The fast protocol ($T_{\mathrm{l}} = 2\,\mathrm{s}$) excites a slow elastic
  ringing of the membrane; at $M = 8$ it damps within the run and reproduces
the paper protocol, but at $M = 16$ it is still $\sim 20\,\%$ above the
plateau at $t = 20\,\mathrm{s}$. All quoted values therefore use the paper
protocol ($T_{\mathrm{l}} = 20\,\mathrm{s}$, $T_{\mathrm{f}} = 50\,\mathrm{s}$).
* The element Jacobians here are computed on the quadratic ($\mathbb{Q}^2$)
  Lagrangian mesh, so they are not pointwise comparable with the reference's
  $\mathbb{Q}^1$ Jacobian maps; the range and the location of the largest
  errors are.
* As in demo_443, the effective incompressibility of the reference is carried
  by the material bulk in this FE-coupled variant. The calibration check
  (§4.3) shows the Cook's corner displacement is sensitive to it in the same
  direction as the reference's own stabilisation treatment (its stabilised
  curves sit high, its unstabilised low), and that at matched volume
  behaviour a residual $\approx 0.09\,\mathrm{cm}$ remains. All quantities
  here are CGS and the compression case required the opposite volume
  adjustment, so no global unit factor can account for either observation.

## References

{{< references >}}
