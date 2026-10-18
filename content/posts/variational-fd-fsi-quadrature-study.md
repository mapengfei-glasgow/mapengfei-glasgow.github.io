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

**Current result:** more interaction points improve integration, but do not
replace the solid degrees of freedom needed to resolve deformation. All six
full Cook pilot runs completed. Their results do not establish superiority
over the original nodal IB-4 coupling. GPU coupling speedup remains unproven:
fluid and constitutive kernels run on GPU, while this reference adapter
assembles coupling and solves the solid mass system on CPU.

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

## Research plan

The next stages are joint fluid/solid refinement, cell-aware quadrature,
fixed-support temporal studies, full-load torsion/LV validation, and comparison
with quadrature-based IB methods in addition to the nodal baseline. A scalable
CUDA coupling implementation needs device assembly/reduction and an appropriate
sparse mass solve; the current dense host reference is capped at 2000 nodes.

A publication-level efficiency claim requires repeated warmed timings,
component costs and memory use at comparable verified accuracy. A JCP paper
would need a distinct contribution and evidence beyond established dense
quadrature or adjoint transfer. These results document progress and limitations;
they are not a claim of publication readiness.
