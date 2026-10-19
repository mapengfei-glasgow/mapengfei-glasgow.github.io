---
title: "Variational FD–solid coupling: coarse meshes, quadrature and volume conservation"
description: "Controlled GPU-fluid experiments test dense interaction quadrature, identify a body-advection defect, and separate integration accuracy from solid-mesh resolution."
date: 2026-10-19T00:00:00+08:00
academic: true
ShowToc: true
TocOpen: false
tags: ["FSI", "GPU", "verification", "finite elements"]
---

Can a coarse finite-element solid mesh interact accurately with a finer
Cartesian fluid grid if we use more Gauss points inside each solid element?
This study tests that idea using an existing finite-difference GPU fluid
solver and an isolated P1 tetrahedral variational coupling adapter.

**Current result:** dense interaction quadrature improves transfer integration,
but cannot replace the solid resolution needed for deformation. Optional CUDA
transfer and dense mass-inverse implementations now match the CPU reference.
All eight joint-refinement cases complete at a common stable time step, but
strong solid-mesh sensitivity remains. The first adaptive quadrature selector
reduces local stencil error without a consistent cost advantage over uniform
subdivision. Whole-solver speedup at matched accuracy remains unproven.

## Method and established prior work

The adapter integrates fluid/solid interaction in the solid reference domain,
without explicitly evaluating a regularized delta kernel. With reference
consistent mass M and interaction matrix C, solid velocity is M^-1 C u.
The fluid force uses the negative adjoint, -C^T M^-1 g/h^3, where g is the
assembled elastic/load gradient under the driver's sign convention.
The two maps use identical quadrature stencils and satisfy a discrete work
identity. That identity alone guarantees neither incompressibility nor
stable time stepping.

This follows the variational framework of
[Roy, Heltai and Costanzo](https://arxiv.org/abs/1306.0936v3).
Dense interaction quadrature on coarser structural meshes is already part of
[hybrid FD/FE immersed-boundary work](https://arxiv.org/abs/1612.05916) and
[IFED coupling studies](https://arxiv.org/abs/2105.14536).
[Divergence-free interpolation with adjoint spreading](https://arxiv.org/abs/1701.07169)
is also established. Those features alone are not claimed as new.

## Controlled Cook comparison

The tapered solid has vertices (0,0), (4.8,4.4), (4.8,6.0), (0,4.4) cm
in its cross-section and thickness 1 cm. It is immersed in a 12 cm cubic
fluid domain with 16 cells per direction. Fluid density is 1 g/cm³ and
dynamic viscosity .16 g/(cm·s). The anisotropic material uses Gt=8, Gl=160,
El=1200 dyn/cm² and fibre direction (1,1,1)/sqrt(3), with the existing
modified-invariant formulation and volumetric stabilization.

**Boundary conditions:** the left solid face is fixed by a penalty with
physical stiffness 1,875,000 dyn/cm³. The right face receives +y traction
6.25 dyn/cm², smoothly ramped over 14 s; other solid faces are traction-free.
The outer fluid walls are stationary no-slip. Pressure correction uses the
existing homogeneous Neumann treatment and solver gauge. Both fluid and solid
start at rest. All methods use dt=.001 s and end at 35 s, including relaxation
after the ramp. The original geometry update is retained for this comparison.

The n4 mesh has 50 nodes/96 tetrahedra; n8 has 243 nodes/768 tetrahedra.
Only interaction quadrature changes between the two variational runs:
27 versus 125 points per tetrahedron. Constitutive P1 stress integration and
face-load integration are unchanged. IB-4 is a baseline, not an exact solution.

| Solid / coupling | Loaded-corner y displacement (cm) | Solid volume change (%) | Single wall time (s) |
| --- | ---: | ---: | ---: |
| n4 / original IB-4 | 1.30243458 | .6565203 | 249.7 |
| n4 / variational, 27 points | 1.29915836 | .6092625 | 295.5 |
| n4 / variational, 125 points | 1.29893877 | .6060515 | 473.6 |
| n8 / original IB-4 | 1.35503837 | .0822934 | 241.5 |
| n8 / variational, 27 points | 1.37188263 | .1200009 | 646.4 |
| n8 / variational, 125 points | 1.37153838 | .1097262 | 2185.9 |

More quadrature changes corner displacement by less than .026% on either
mesh; solid refinement changes it by approximately 4–6%. Variational volume
drift is smaller on n4 and larger on n8 relative to IB-4. Maximum fixed-base
displacement is below 5.72e-5 cm across the six trials. Residual velocities
remain, so the endpoint is not demonstrated equilibrium.

Wall times include initialization and output. Short geometry controls shared
the GPU during the first baseline trial. These are single pilot measurements
of a CPU coupling adapter plus GPU fluid solver, not controlled speedups.
A fixed-fluid-grid/two-solid-mesh comparison is insufficient for a converged
reference or a physical accuracy ranking.

![Cook displacement, volume and minimum J histories](/images/variational-fd-fsi/cook_comparison.png)

[Download commands, completion status and measured quantities](/data/variational-fd-fsi/cook_summary.json).

## Separate integration error from solid approximation

Twenty-four manufactured projections use an analytic divergence-free field
on three Cook meshes, two wavelengths and four quadrature orders. High-order
projections are checked for agreement, and analytic-field approximation error
is integrated separately.

For a deliberately oscillatory 3 cm wavelength on the 18-node mesh, increasing
27 to 125 points reduces quadrature error from 9.55% to .21%, but the P1
reference projection still differs from the analytic field by 76.7% in L2.
For the smoother 12 cm wavelength, reference P1 errors decrease from 21.2%
to 5.49% to 1.35% with solid refinement. Dense integration cannot recover a
field absent from the approximation space.

![Quadrature error versus P1 approximation error](/images/variational-fd-fsi/quadrature_accuracy.png)

Another 24 projections integrate actual trilinear MAC reconstructions across
nonmatching cells. Increasing 27 to 125 points helps all four tested mesh/grid
configurations, but convergence is slower than for the smooth analytic input.
Order-25/33 disagreement is reported as reference uncertainty; neither is
assumed exact. Cell-aware integration and translated placements need testing.

[Analytic projection data](/data/variational-fd-fsi/quadrature_accuracy.json) ·
[MAC cell-crossing data](/data/variational-fd-fsi/cell_crossing_accuracy.json).

## A verified geometry-update correction

A manufactured steady-advection test exposed a first-order body update in
the inherited driver, despite its midpoint comment. Its two successive half
steps do not equal explicit midpoint for spatially varying velocity.
An optional correction evaluates old and new fluid velocities at the same
predicted midpoint and averages them for the full position update.

Three short active-LV controls use global volume constraints, the same
material/mesh, N32, fixed physical support stiffness, and endpoint .02 s:

| Update | dt (s) | Solid volume change (%) |
| --- | ---: | ---: |
| Legacy | .0001 | 1.1463e-5 |
| Corrected midpoint | .0001 | 1.2592e-7 |
| Corrected midpoint | .00005 | 3.1481e-8 |

The correction reduces volume drift about 91-fold at equal dt, and halving
dt reduces its residual by a factor four. Independent checkpoint projection
matches stored velocities to 6.89e-15 cm/s. These are early-ramp tests, not
full-load LV validation or proof of full coupled second-order accuracy.
The option remains experimental and was not used in the Cook comparison.

[Geometry-control commands and independent audits](/data/variational-fd-fsi/geometry_summary.json).

## Local incompressibility remains unresolved

Independent audits show that the continuous P1 mass projection can introduce
solid divergence even from a divergence-free reconstructed fluid field.
Changing to a lowest-order RT0 reconstruction alone does not cure it.
Global or regional solid-volume constraints preserve instantaneous volume
rates with a matching force adjoint, but individual tetrahedra can still
compress and expand.

In short active-LV tests, 52 regional constraints reduce local volume RMS
error from 3.31% with global control to 2.35%. Worst compression improves,
while worst expansion increases. Passive LV does not improve consistently.
This is an experimental tradeoff, not demonstrated physical superiority.

![Global and regional volume-control comparison](/images/variational-fd-fsi/comparison.png)

## GPU implementation and common-step refinement

The isolated coupling adapter now supports device stencil construction and
optional dense GPU mass actions. All 36 small operator combinations pass
reference and work checks. Six matched short trajectories for the precomputed
inverse differ from CPU final coordinates by at most 4.67e-15 cm. This verifies
implementation agreement, not physical accuracy. Dense storage and the
2000-node reference cap remain; geometry-dependent volume-constraint
preparation still runs on CPU.

The active-LV pilot varies solid layers (290 or 1731 nodes), fluid N32/N64 in
a 4 cm cube, and 27/125 interaction points per tetrahedron. All eight cases
reach .1 s at dt=.000025 s and pass independent checkpoint audits. Fluid
walls remain stationary with no slip. The material, .5 s pressure/activation
ramp and support stiffness are held fixed: rho=1 g/cm³, viscosity=.04
 g/(cm·s), Guccione C=2e4 dyn/cm², bf=8, bt=2, bfs=4,
bulk modulus=93333.33 dyn/cm², final active stress=6e5 dyn/cm² and final
pressure=1.5e5 dyn/cm². The basal surface uses a nodal-lumped penalty with
physical stiffness 31,250,000 dyn/cm³; it is not an exact clamp. Global volume
control and the corrected midpoint geometry update are used throughout.

At the endpoint, apex displacement is approximately -.004 cm on the coarse
solid and +.22 cm on the finer solid. Solid refinement changes geometry and
fibre representation as well as structural resolution. These are transient
pilot results, not a converged reference or validated cardiac prediction.
On the finest 125-point case, half-step versus quarter-step apex displacement
differs by 2e-8 cm; the large mesh sensitivity persists beyond this time-step
check. Local J error does not consistently improve with fluid refinement.

![Joint refinement at the same stable time step](/images/variational-fd-fsi/common_dt_refinement.png)

[Exact commands, binary hashes and nine endpoint audits](/data/variational-fd-fsi/common_dt_summary.json).

## Explaining the initial stability failures

At dt=.0001 s, three of the original eight combinations invert. CPU and GPU
reproduce the same rapid growth. Reducing dt lets all three reach .1 s without
weakening material or support stiffness.

An independent initial linear model includes the passive elastic tangent,
actual basal penalty and an exact MAC normal-wall pressure projection. Its
inviscid oscillator limits classify all eight original outcomes correctly.
For the coarse solid on N64, it estimates dt limits of 9.44e-5 s with 27
points and 1.10e-4 s with 125 points, bracketing the tested 1e-4 s step.
This model excludes viscosity, convection, evolving geometry and load; it is
not a nonlinear stability guarantee.

Reference mass-whitened transfer gain also reveals quadrature amplification:
on coarse-solid N64 its squared norm is 1.378 with 27 points and .943 with
125 points before pressure projection. Gain alone does not determine stable
dt; stiffness also matters.

![Reference-state squared transfer gain](/images/variational-fd-fsi/coupling_gain.png)

[Dense reference-model checks](/data/variational-fd-fsi/projected_reference_stability.json) ·
[Residual-verified Lanczos frequencies](/data/variational-fd-fsi/lanczos_reference_frequency.json).

## First adaptive quadrature selector: error improves, cost remains a problem

A field-independent selector integrates the complete local transfer stencil,
compares 27/125-point rules and bisects the longest tetrahedral edge when
its estimator is too large. Leaves wholly inside the component interpolation
cells use polynomial-exact 125-point integration. The depth limit is 12.
The estimator is not a certified error bound. Selection depends on geometry,
not the velocity or force right-hand side, so the same matrix can supply
interpolation and its transpose force map.

Four distributed coarse-LV tetrahedra, two fluid spacings and two translations
provide 16 configurations. Independent checks verify partition, affine
moments and transpose work to roundoff. These are local integration tests,
not coupled simulations with the adaptive rule.

| Rule | Median relative local-stencil error | Evaluated points per tetrahedron |
| --- | ---: | ---: |
| Fixed 27 | .2581 | 27 |
| Fixed 125 | .03851 | 125 |
| Uniform subdivision level1 | .008413 | 1,000 |
| Uniform subdivision level2 | .001342 | 8,000 |
| Uniform subdivision level3 | .0002692 | 64,000 |
| Adaptive tolerance .01 | .002006 | 1,976–63,384 |
| Adaptive tolerance .003 | .0003864 | 12,616–398,696 |

Costs count rejected parent evaluations and estimator work. The reference
uses uniform level4 subdivision with 512,000 points per tetrahedron; its
maximum disagreement with level3 is 8.06e-4. Some small reported errors fall
below that disagreement, so their ranking is uncertain. Tolerances are local
absolute stencil-estimator thresholds normalized by reference volume, not
relative solution-error tolerances.

![Local stencil error against total evaluated point count](/images/variational-fd-fsi/adaptive_error_cost.png)

The tighter rule hits the depth cap on 440 leaves without satisfying its
estimator. Neither tolerance demonstrates a consistent cost advantage over
cheaper uniform rules. This is a useful negative result: the next candidate
should target MAC grid-plane intersections directly before expensive global
stability and nonlinear GPU tests.

[Selected measurements](/data/variational-fd-fsi/adaptive_local_stencil_errors.json) ·
[Summary and source/mesh hashes](/data/variational-fd-fsi/adaptive_summary.json) ·
[Independent operator checks](/data/variational-fd-fsi/adaptive_operator_checks.json).

## Research and publication status

The next gates are structural/geometry convergence, local incompressibility,
grid-plane-aware integration and a matched comparison against existing
quadrature-based immersed coupling. A publication-level efficiency claim
requires total runtime and memory at comparable verified accuracy, including
initialization and constraint costs. Component GPU timings cannot substitute
for that comparison.

Coarse solid meshes with dense interaction points are established prior work.
The current tensor trilinear hats are also algebraically tensor tent kernels;
avoiding explicit delta-function notation alone is not a new method. The
stability diagnosis is promising research evidence, but the results do not
yet establish JCP submission readiness.
