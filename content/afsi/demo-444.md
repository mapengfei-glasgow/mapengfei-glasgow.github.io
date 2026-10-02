---
title: "444: IB2d Rubberband — Fiber and Thick Band"
description: "IB2d's standard oscillating rubberband (64 zero-rest-length springs) solved in AFSI as a 1-D fiber and a thick neo-Hookean annulus, each with three fluid solvers (RT, Chorin, IPCS) — first case of the IB2d comparison series."
date: 2026-10-02
weight: 444
academic: true
demo_id: demo_444
category: Benchmark
dimension: 2D
solid_model: "IB2d zero-rest-length springs (fiber) / prestrain neo-Hookean annulus (thick)"
coupling: "RT nodal coupling E / Eᵀ (divergence-conforming); four-point-kernel IB background kept for comparison"
reference: "IB2d Example_Standard_Rubberband (Battista et al. 2017, 2018)"
status: Complete
tags: ["IB2d"]
---

## 1. Introduction

This is the first case of a new comparison series against **IB2d**
(Battista et al.), the widely used MATLAB/Python implementation of the
immersed boundary method. The case is IB2d's flagship example,
`Example_Standard_Rubberband/Rubberband_with_Springs`: an ellipsoidal
"rubberband" made of 64 Lagrangian markers closed by 64 springs with
**zero resting length**, immersed in a unit box of fluid. It contracts, and
the enclosed fluid resists — a compact test of force spreading,
interpolation, and above all of how faithfully each solver keeps the
**enclosed area** of an incompressible fluid.

AFSI solves the case six times — as the IB2d **fiber** and as a **thick**
continuum band, each with three fluid solvers: the divergence-conforming
RT/DG solver and the two projection schemes (Chorin, IPCS) on the P2/P1 +
four-point kernel background. All six runs are compared against the
registered IB2d run; the projection runs double as the leak test of §4.

{{< figure src="/afsi/demo444-shapes.png" title="Figure 1. Rubberband shape at t = 0.10, 0.20, 0.40, 0.80 and 1.50 s (dotted grey: the initial ellipse) — one row per run: IB2d (registered) and the six AFSI runs {fiber, thick} × {RT, Chorin, IPCS}. The fiber (RT) rings like IB2d and settles onto the equal-area circle, while both fiber projections collapse within 0.14 s (rows 3–4). The thick annulus resists collapse under all three solvers; its timescale is set by the solid, not the fluid solver." >}}

## 2. Setup

IB2d parameters (from the example's `input2d`): `rho = 1`, `mu = 0.01`,
`dt = 1e-3`, `Tfinal = 1.5`, box `1 x 1` with a `32 x 32` grid, four-point
kernel. The structure: 64 markers on the ellipse `x = 1/2 + 0.2 cos θ`,
`y = 1/2 + 0.4 sin θ` (semi-axes $a_x = 0.2$, $a_y = 0.4$, enclosed area
$\pi a b \approx 0.2513$), closed by 64 springs, stiffness
$k = 2.5 \times 10^4$, resting length 0, force density
$f_i = k\,(X_{i+1} + X_{i-1} - 2X_i)$.

AFSI settings: fluid mesh `N = 16` quads whose P2 velocity nodes
(33 × 33, spacing 1/32) sit exactly on IB2d's grid; same `dt`, `rho`, `mu`;
RT/DG velocity–pressure pair (H(div)-conforming, exactly divergence-free
velocity) with the nodal coupling `E` / `Eᵀ`; the two projection runs
(`FLUID=chorin`, `FLUID=ipcs`) use the same P2/P1 pair, the same
four-point-kernel coupling and the same load — only the solver changes.
The thick band: wall
thickness 0.05 (stress-free radii 0.2328 / 0.2828), 96 × 2 polar cells,
neo-Hookean with $\mu_s = 40$, $\kappa_{stab} = 400$, prestrained by the
affine map that puts its outer edge on the IB2d ellipse. One setup
difference is kept deliberately: IB2d's box is periodic, AFSI's has no-slip
walls (the band stays inside $|X-1/2| \le 0.4$).

## 3. The spreading weight — convention verified two ways

IB2d's spring output is a force **density**; before spreading it is
multiplied by the constant `ds = min(Lx/(2Nx), Ly/(2Ny))` ("Peskin constant
`ds`", here `1/64`) and then spread with the four-point kernel
(`please_Find_Lagrangian_Forces_On_Eulerian_grid.m`): instrumenting the
running code at the initial state gives `max fx·ds = 0.752` and a grid
force with `max|F_x| = 302.7`. An earlier version of this page read those
numbers as "the realized force is 4× below the textbook spread" — that was
an artifact: a replica of the documented pipeline reproduces `max|F_x| =
302.7` **exactly** and, from the same field, `max|F_y|` = the 2-D
magnitude = 1150.7 ≈ the "1155" hand value. On this tall ellipse
(0.2 × 0.4) the x-component and the magnitude differ by ≈ 4×. AFSI's
`DS = 1/(4N) = 1/64` therefore uses IB2d's own convention — verified by
dynamics: marker oscillation period 0.201 s vs IB2d 0.190 s; first/second
`a_x` peaks 0.106 s / 0.302 s vs IB2d 0.10 s / 0.32 s. (An earlier
internal calibration used `DS = 1/256`, which under-forced the fiber 4×
and doubled the period; the runs here use the verified value.)

## 4. The enclosed area separates the solvers

{{< figure src="/afsi/demo444-area.png" title="Figure 2. Seven curves per panel: IB2d + the six AFSI runs. Left: enclosed area. Second: relative area error (log). Third/fourth: semi-axes a_x, a_y. Only the RT runs hold the enclosed area (fiber −7 %, thick −0.15 %); both projection flavours leak — the fiber collapses by 0.14 s, the thick annulus loses 4.7 % — and Chorin ≡ IPCS on both shapes (their curves overplot)." >}}

For an incompressible fluid, the enclosed area can only change through the
velocity sampled **at the markers**. A projection method enforces
divergence-freedom only against its pressure test functions: the marker
velocity then carries sub-cell divergence, and the enclosed area leaks at
exactly the rate $\int \nabla\cdot u$ over the band. Measured: −20.8 % in
0.02 s at $N = 16$ for the P2/P1 + IB4 run — the leak rate matches the FEM
velocity's residual divergence, and it collapses the band by $t = 0.14$ s.

Refinement does not heal it. With the same physical load the leak at
t = 0.02 s is −20.8 % / −9.4 % / −7.7 % for N = 16 / 32 / 64 (IB2d's
spectral projection at the same time: **+0.03 %**; the RT solver:
**−0.56 %**) — and it is dt-converged as well: dt = 1e-3 / 2e-4 / 1e-4
give −20.8 % / −20.9 % / −20.9 % at the same time. Refinement reduces the
leak but never approaches divergence-freedom — consistent with the Q2/Q1
pair on quadrilaterals not being inf-sup stable, so the pressure space
cannot see every divergence the velocity space can produce. The
incremental pressure-correction flavour (IPCS) is no different: −20.5 % at
N = 16 and −8.9 % at N = 32, essentially identical to standard Chorin —
the defect belongs to the velocity/pressure pair and the marker sampling,
not to the projection flavour or the time step. It is also not a defect of
the kernel or the force (which was verified against the instrumented IB2d
run, §3). The same defect runs through both shapes: over the full window
the unsupported fiber collapses to 5 % of its area by $t = 0.14$ s while
the thick annulus loses 4.7 % of its enclosed area (Chorin −4.71 %,
IPCS −4.70 %) against −0.15 % for RT.

The RT velocity is divergence-free **by construction**, and the leak is
two orders of magnitude smaller: −0.56 % at 0.02 s, −7.1 % after the full
1.5 s with the tensioned fiber, and −0.15 % for the thick band. Over the
same window the registered IB2d run loses **27 %**: its spectral projection
is divergence-free, but the kernel-smoothed marker velocity still carries
a sub-cell divergence and the band drains inward (mostly after
$t \approx 0.3$ s).

## 5. Results

| run | $a_x$ at 0.2 s | $a_y$ at 0.2 s | area at 1.5 s | final shape |
|---|---:|---:|---:|---|
| IB2d fiber (registered) | 0.2159 | 0.3604 | 0.1840 (−26.8 %) | still creeping |
| AFSI fiber (RT) | 0.2235 | 0.3412 | 0.2335 (−7.1 %) | circle $R = 0.279$ |
| AFSI fiber (Chorin) | 0.018 | 0.014 | 0.000004 (−100 %) | collapsed by $t = 0.14$ s |
| AFSI fiber (IPCS) | 0.020 | 0.016 | 0.000000 (−100 %) | collapsed by $t = 0.14$ s |
| AFSI thick (RT) | 0.2452 | 0.3308 | 0.2510 (−0.15 %) | circle $R = 0.283$ |
| AFSI thick (Chorin) | 0.2217 | 0.3129 | 0.2395 (−4.7 %) | still creeping |
| AFSI thick (IPCS) | 0.2220 | 0.3131 | 0.2395 (−4.7 %) | still creeping |

- **Physics check.** A zero-rest-length band at a fixed enclosed area
  minimises its spring energy $\tfrac{k}{2}\sum s_i^2 \propto$ perimeter²
  when it is the **circle** of that area: $R = \sqrt{A_0/\pi} = 0.2826$.
  The AFSI fiber settles onto $R = 0.279$ — the equal-area circle — through
  a large damped aspect-ratio oscillation (the ellipse's sides bulge out,
  overshoot, and ring down with a 0.19-s period). The thick annulus
  settles onto its stress-free circle, $R_{out} = 0.2828$; the two models
  therefore share the same equilibrium radius family by construction.
- **Agreement with IB2d.** With the spreading weight calibrated to IB2d's
  own convention (§3) the two rings oscillate in phase at the same
  ~0.2-s period: first and second $a_x$ peaks at 0.106 s / 0.302 s (AFSI)
  vs 0.10 s / 0.32 s (IB2d), with similar decay envelopes
  ($0.36 \to 0.28$ vs $0.38 \to 0.28$ over 1.1 s) and matching values at
  $t = 0.2$ s ($a_x$: 0.224 vs 0.216, $a_y$: 0.341 vs 0.360). The
  late-time divergence is IB2d's own enclosed-area drift: its 27 % loss
  shrinks the band (its period drifts to 0.18 s), while the RT band holds
  its area to −7.1 %.
- **The failure mode.** The projection runs are shown for exactly one
  lesson: at this force scale a P2/P1 (Taylor–Hood on quads) velocity
  cannot keep an immersed closed band's area — the defect is in the
  sampled divergence, not in the kernel or the time step. The unsupported
  fiber collapses to 5 % of the initial area by $t = 0.14$ s; the thick
  annulus cannot collapse (its elasticity holds the ring) but still drains
  4.7 % of the enclosed area, and Chorin and IPCS agree to 0.01 %.

{{< figure src="/afsi/demo444-velocity.png" title="Figure 3. Maximum marker speed |dX/dt| (finite differences of the dumped marker paths — a kinematic measure comparable across codes) — seven curves. IB2d and the fiber (RT) ring down at the same ~0.2-s period with similar peaks (≈3 m/s); the fiber projections die within 0.15 s; the three thick runs share the elastic time scale and never collapse." >}}

## 6. Caveats

- Single resolution (N = 16), single MPI rank, prototype settings; not a
  convergence study.
- Periodic (IB2d) vs no-slip (AFSI) outer boundaries.
- The IB2d software path was verified by instrumenting the example code
  and by a direct replica of the documented spreading pipeline (§3); the
  default spreading weight uses IB2d's own constant-`ds` convention.
- The damping comparison is qualitative: IB2d's dissipation combines
  kernel smoothing, the spectral projection and its RK2 scheme.

## 7. Reproduction

```bash
# AFSI (from afsic/demo/demo_444)
python main.py                      # fiber, RT (default)
SHAPE=thick python main.py          # thick annulus, RT
FLUID=chorin python main.py         # fiber, Chorin
FLUID=ipcs python main.py           # fiber, IPCS
SHAPE=thick FLUID=chorin python main.py   # thick, Chorin
SHAPE=thick FLUID=ipcs python main.py     # thick, IPCS
IB2D_DIR=<...>/Rubberband_with_Springs python plot_compare.py

# IB2d (from its example directory)
matlab -batch "main2d"
```
