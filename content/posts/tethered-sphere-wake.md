---
title: "Flow past a tethered rigid sphere: GPU wake simulation at Re=1000"
description: "Actual wake animation and PyVista Q-criterion views, with sphere motion, boundary conditions, spring/damper coupling and explicit accuracy limits."
date: 2026-10-16T00:00:00+08:00
academic: true
ShowToc: true
tags: ["CFD", "GPU", "sphere", "Q-criterion"]
---

This trial simulates flow past a translating rigid sphere attached to an
ideal spring and damper. The GPU calculation completed 7,500 steps on a
96 × 96 × 192 grid, reaching $tU/D=15$ and saving 51 velocity frames.
The sphere oscillates against its tether and produces an unsteady wake with
shed vortical structures.

**Status:** an exploratory wake and rigid-body coupling trial. Turbulence,
DNS accuracy and quantitative surface-force accuracy remain unconfirmed.
The sphere has only 16 grid cells across its diameter.

{{< figure src="/tethered-sphere/wake-evolution.gif" title="Actual simulated vorticity magnitude on a slice through the moving sphere's centre in y. Flow is in +z, to the right. The grey disc marks the sphere. The colour scale is fixed across frames, using a robust percentile that clips rare extremes. Playback speed is illustrative." >}}

{{< figure src="/tethered-sphere/wake-Q.png" title="PyVista Q=0.5 wake isosurfaces at t=15, coloured by vorticity magnitude on a fixed 0–12 scale. The grey sphere is shown at its simulated position. The surface is restricted to the downstream fluid region; positive Q alone does not establish turbulence." >}}

## Domain and flow conditions

The sphere has diameter $D=1$, radius 0.5, reference inflow speed $U=1$,
and fluid density 1. The domain is $[0,6]\times[0,6]\times[0,12]$;
flow is in **positive z**. Viscosity is $\nu=0.001$, giving
$Re_D=UD/\nu=1000$. All times are nondimensional in $D/U$.

Initial fluid velocity and pressure are zero. The inflow reaches full speed
over the first time unit, with

$$
U(t)=s^2(3-2s),\qquad s=\min(1,\max(0,t)).
$$

## Boundary conditions

| Boundary | Velocity treatment | Pressure-correction treatment |
|---|---|---|
| Inlet, z=0 | Prescribed $(0,0,U(t))$ | Homogeneous Neumann |
| Sides, x=0 and x=6 | Prescribed coflow $(0,0,U(t))$ | Homogeneous Neumann |
| Sides, y=0 and y=6 | Prescribed coflow $(0,0,U(t))$ | Homogeneous Neumann |
| Outlet, z=12 | Solver's PhysicalOpen treatment | Homogeneous Dirichlet correction, with physical pressure p=0 |

The sides approximate a finite-distance outer flow: they are neither
stationary side walls nor periodic boundaries. Sphere projected area divided
by box cross-section area is about 2.18%; this alone does not establish
negligible boundary influence.

The outlet pressure patch covers the complete rectangular face. The solver
uses free tangential velocity treatment and normal divergence-free boundary
reconstruction there. Pressure is incrementally updated, with its reference
set by the outlet pressure condition.

A sponge acts over $10<z<12$:

$$
\mathbf{f}_{\rm sponge}=-\sigma(z)(\mathbf{u}-U(t)\mathbf{e}_z),\qquad
\sigma=2\left[\min(1,\max(0,(z-10)/2))\right]^2.
$$

The sponge force is excluded from the sphere reaction. It reduces wake
disturbances before the outlet, but it also modifies the downstream flow.
The convection implementation still fills outer ghosts from its prescribed
boundary policy; this is **not a verified nonreflecting outlet**. Boundary
distance and outlet/sponge sensitivity need separate checks.

## Sphere and tether model

The virtual anchor is $(3,3,3)$. The initial sphere centre is $(3.02,3,3)$,
with zero translational velocity. The small x offset breaks exact axial
symmetry. The initial y symmetry is not deliberately broken, which may
constrain wake modes.

The sphere is rigid, translates in all three directions and has fixed
rotation. There is no deformation, gravity, contact, or explicitly meshed
tether filament. The restoring force is

$$
\mathbf{F}_{\rm tether}=-5(\mathbf{X}-\mathbf{X}_a)-0.4\mathbf{V}.
$$

The anchor lies at the reference centre; this is an ideal centring
spring/damper model, not a string connected to an external support.
Nominal solid density is 4 and nominal solid mass is $4\pi/6$.

### Fluid–body coupling

The analytic sphere uses regularized volume penalization on the existing
staggered GPU grid:

$$
\mathbf{f}_{\rm penalty}=100\chi(\mathbf{V}-\mathbf{u}).
$$

The mask is one for $r\le R-h/2$, zero for $r\ge R+h/2$, and smoothstep
between. It is evaluated separately on each velocity component's staggered
faces. The opposite volume-integrated penalty force drives the body, and the
updated centre changes the next step's mask. The coupling is bidirectional.

The approximate component-wise effective mass is

$$
m_{{\rm eff},c}=4\frac{\pi}{6}-\sum\chi_c h^3.
$$

This fictitious-fluid inertia correction assumes that interior fluid follows
the sphere. It is not a separately validated added-mass model. Finite slip,
regularization and split coupling introduce error. The spring/damper update
is semi-implicit, while fluid forcing uses the preceding body state.

Logged `reaction_*` values are penalty reactions, not independently validated
surface tractions or drag coefficients. The experiment does not use an elastic
finite-element sphere or the repository's sphere mesh.

## Runs and numerical settings

| Setting | Pilot | Main |
|---|---|---|
| Grid | 48 × 48 × 96 | 96 × 96 × 192 |
| Cells per sphere diameter | 8 | 16 |
| Time step | 0.002 | 0.002 |
| Final time | 2 | 15 |
| Saved frames | 11 | 51 |

Both runs use double precision, FMA, AB2 second-order-upwind convection,
backward-Euler viscosity, three Helmholtz cycles, ten pressure cycles and
three pressure smoothing sweeps. Pressure means use device reduction.
No turbulence closure is added, and $\Delta t\kappa=0.2$.

The main run took 330.4 seconds, excluding analysis, on an RTX 5070 Laptop
with driver 595.99.02, CUDA compiler 13.1 and g++-13. All saved velocity
fields were finite and no broad numerical failure guard triggered.

## Measured sphere response and wake variation

{{< figure src="/tethered-sphere/diagnostics.png" title="Sphere displacement, penalty reaction, spatial wake crossflow and numerical diagnostics. The penalty reaction is an approximate coupling quantity; spatial crossflow is not a turbulence statistic." >}}

| Main-run measurement | Value |
|---|---|
| Maximum logged integrated MAC divergence L2 | $9.86\times10^{-14}$ |
| Maximum logged speed | 1.39672 U |
| Maximum logged tether displacement | 0.25441 D |
| Final sphere centre | (2.98099, 3.00000, 3.07303) |
| Maximum logged core-slip RMS | 0.01672 U |
| Final core-slip RMS | 0.00785 U |
| Final spatial wake transverse-speed RMS | 0.25865 U |
| Temporal vector-velocity RMS in the sampled wake box | 0.17109 U |

Core slip samples $r<R-h$ and compares interpolated fluid velocity with body
velocity. The spatial wake statistic samples $X_z+0.75<z<X_z+4$,
$|x-X_x|<1$, $|y-X_y|<1$; steady crossflow contributes to it.

The temporal statistic uses 26 snapshots over $t=7.5$–15 in the fixed box
$2<x<4$, $2<y<4$, $4<z<8$. At each point, the sample-mean velocity is
subtracted, component variances are summed, and the result is volume-averaged
before taking the square root. The **17.1%** variation includes coherent
shedding, tether motion and possible mean-flow evolution. It is not a
converged turbulent fluctuation statistic.

After the ramp, inlet and outlet flux are both 36 at the printed precision
of the log. The reported zero relative difference is precision-limited;
it does not assert exact equality of unrounded floating-point integrals.

## What the pictures establish

The actual-frame animation and Q figure show an unsteady wake with shed
vortical structures. They do not establish fully developed turbulence.
The sphere remains largely symmetric in y, and the short observation interval
includes continuing coupled-body dynamics.

Sixteen cells across the sphere diameter do not adequately resolve its
Re=1000 boundary layer for a DNS claim. The pilot ends at t=2, so it cannot
establish convergence of the later wake. Grid, time-step, interface and
penalty refinement, longer averaging, boundary-distance tests and controlled
three-dimensional perturbations are required before stronger conclusions.

The Q figure uses $Q=\tfrac12(\|\Omega\|^2-\|S\|^2)$ computed with PyVista
from cell-centred saved velocity. The plotted threshold is 0.5, restricted to
fluid downstream of the sphere, $z>X_z+0.6$ and $z<9.8$. Threshold and region
are visualization choices. Moving-solid shear and startup transients should
not be interpreted as turbulent wake development by appearance alone.

## Reproduce and download

Study source is committed in workspace revision `33845d8`, using GPU solver
revision [`cd6f637`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/tree/cd6f637d3009e46f84d437136a669217003f72ea).
From `studies/tethered-sphere/` in the workspace:

```bash
/usr/local/cuda-13.1/bin/nvcc -std=c++17 -O3 -arch=sm_120 \
  -ccbin /usr/bin/g++-13 -fmad=true -I../../fdm-3d-v1-gpu/src \
  sphere_flow.cu -o sphere_flow
./sphere_flow 8 2 0.002 runs/pilot8 100 1000
./sphere_flow 16 15 0.002 runs/main16 150 1000
python3 analyse.py runs/main16
```

Arguments are cells per diameter, final time, time step, output directory,
frame interval and diameter Reynolds number. Existing output directories are
rejected. Analysis uses NumPy, Matplotlib, Pillow and PyVista/VTK, supporting
normal package installations and this workspace's isolated environment.

Raw frames are float32 interpolated cell-centred velocity in z,y,x,component
order; the solver itself uses double precision. The frame index records actual
times and sphere centres. Analysis exports a ParaView `fluid.pvd` series.
Full field files remain local; figures, scripts and diagnostic tables are
published below.

- [Wake animation](/tethered-sphere/wake-evolution.gif) · [PyVista Q figure](/tethered-sphere/wake-Q.png) · [Motion and diagnostics figure](/tethered-sphere/diagnostics.png)
- [Summary JSON](/tethered-sphere/summary.json) · [Main diagnostics](/tethered-sphere/main16-diagnostics.csv) · [Main metadata](/tethered-sphere/main16-metadata.json) · [Main frame index](/tethered-sphere/main16-frames.csv)
- [Pilot diagnostics](/tethered-sphere/pilot8-diagnostics.csv) · [Pilot metadata](/tethered-sphere/pilot8-metadata.json) · [Pilot frame index](/tethered-sphere/pilot8-frames.csv)
- [GPU driver](/tethered-sphere/sphere_flow.cu) · [Analysis script](/tethered-sphere/analyse.py) · [Detailed run notes](/tethered-sphere/README.md)

Related: [lid-driven cavity with a tethered sphere](/posts/lid-driven-cavity-sphere/)
and [3D vortex decay](/posts/gpu-vortex-decay-q-criterion/).
