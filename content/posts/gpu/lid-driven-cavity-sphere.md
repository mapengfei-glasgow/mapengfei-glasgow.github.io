---
title: "Lid-driven cavity with a tethered rigid sphere: GPU simulation and Q-criterion"
description: "A 96³ GPU cavity experiment with an actual-frame animation, velocity streamlines, PyVista Q surfaces, and explicit boundary and sphere-coupling conditions."
date: 2026-10-16T00:00:00+08:00
academic: true
ShowToc: true
tags: ["CFD", "GPU", "sphere", "Q-criterion"]
url: /posts/lid-driven-cavity-sphere/
area: "research"
readingRoute: "gpu-solver"
areas: ["Computational Fluid Dynamics"]
noteType: "Verification"
---

This experiment places a spring/damper-tethered rigid sphere inside a unit
lid-driven cavity. The moving top wall drives circulation around the sphere.
The GPU calculation completed 10,000 steps on a 96³ grid, reaching
$tU_{\rm lid}/L=10$ and saving 41 velocity frames.

**Result:** stable cavity circulation with a small sphere response.
Turbulence, steady state and benchmark accuracy have not been established.
The sphere uses approximate volume-penalty coupling, with fixed rotation.

{{< figure src="/lid-driven-sphere/cavity-evolution.gif" title="Actual simulated mid-plane speed and sphere position through t=10. The top lid moves in +x, indicated by the red arrow. The colour scale remains fixed at 0–1. Playback speed is illustrative." >}}

{{< figure src="/lid-driven-sphere/cavity-flow.png" title="Velocity magnitude and instantaneous in-plane streamlines near z=0.5 at t=10. The lid produces clockwise circulation around the rigid sphere, with secondary recirculation. These streamlines are not particle trajectories." >}}

{{< figure src="/lid-driven-sphere/cavity-Q.png" title="PyVista Q=0.5 isosurfaces at t=10, coloured by vorticity magnitude on a fixed 0–20 scale; larger values saturate. The grey sphere is partly obscured by the surfaces. Strong near-lid and corner structures are present. Positive Q alone does not establish turbulence." >}}

## Domain and boundary conditions

The domain is $[0,1]^3$, with fluid density 1 and kinematic viscosity
$\nu=0.001$. Final lid speed is 1, giving the cavity Reynolds number
$Re_L=U_{\rm lid}L/\nu=1000$. All quantities and times are nondimensional.

| Boundary | Prescribed velocity |
|---|---|
| Top, y=1 | $(U_{\rm lid}(t),0,0)$ |
| Bottom, y=0 | $(0,0,0)$ |
| Left/right, x=0 and x=1 | $(0,0,0)$ |
| Front/back, z=0 and z=1 | $(0,0,0)$ |

Every wall is impermeable and no-slip relative to its prescribed motion.
There is no inlet, outlet, periodic direction or downstream sponge. The lid
ramps from rest over the first time unit:

$$
U_{\rm lid}(t)=s^2(3-2s),\qquad s=\min(1,\max(0,t)).
$$

Initial fluid velocity and pressure are zero. The standard tangential
discontinuity remains where the moving lid meets stationary walls; near-edge
gradients should therefore be interpreted cautiously.

The incremental projection uses homogeneous Neumann pressure-correction
conditions on all six faces. It removes the Poisson RHS compatibility mean
and the correction's constant nullspace; pressure is updated incrementally
and maintained at zero mean, with homogeneous Neumann pressure ghosts.
These describe the algorithm's numerical pressure treatment and gauge.
Pressure accuracy was not independently validated.

## Sphere and tether model

The sphere has radius 0.18 and diameter 0.36. Its virtual anchor is
$\mathbf{X}_a=(0.5,0.5,0.5)$, with initial centre $(0.505,0.5,0.5)$ and
zero body velocity. The small initial offset excites the restoring spring.
Nominal solid-to-fluid density ratio is 4.

The sphere translates in three directions, with rotation held fixed.
There is no deformation, gravity or contact. The tether force is

$$
\mathbf{F}_{\rm tether}=-(\mathbf{X}-\mathbf{X}_a)-0.05\mathbf{V}.
$$

This is an ideal centring spring/damper. There is no explicitly meshed
tether filament or its fluid drag.

Inside the diffuse sphere the fluid receives
$\mathbf{f}_{\rm penalty}=200\chi(\mathbf{V}-\mathbf{u})$.
The mask is one inside $r<R-h/2$, zero outside $r>R+h/2$, and smoothstep
between. Its reaction drives the sphere. The translational update applies
an approximate component-wise fictitious-fluid inertia correction,

$$
m_{{\rm eff},c}=4\frac{4\pi R^3}{3}-\sum\chi_c h^3.
$$

This assumes that fluid inside the body follows its motion. Finite slip,
the diffuse interface and split coupling introduce modelling error; it is
not an independently validated added-mass model. Spring and damper are
integrated semi-implicitly, while fluid forcing uses the preceding body state.
The logged penalty reaction is not a validated surface traction.

### Relationship to the repository's sphere example

The existing `demo/lid_cavity_sphere.cu` models an elastic immersed sphere,
but its required geometry directory was absent in this checkout. This study
uses an analytic rigid sphere and the coupling developed for the preceding
through-flow trial. It does **not** claim to have run the elastic-sphere demo.

The diameter-based Reynolds number using lid speed would be 360; actual flow
near the sphere is slower and nonuniform. The stated Re=1000 refers to the
cavity length and final lid speed.

## Runs, numerical settings and checks

| Setting | Pilot | Main |
|---|---|---|
| Grid | 64³ | 96³ |
| Time step | 0.001 | 0.001 |
| Final time | 2 | 10 |
| Steps | 2,000 | 10,000 |
| Saved frames | 21 | 41 |

Both use double precision, FMA, AB2 second-order-upwind convection and
backward-Euler viscosity. Each step uses three Helmholtz cycles and ten
pressure cycles with three smoothing sweeps; pressure means are reduced on
the device. There is no turbulence closure. Here $\Delta t\,\kappa=0.2$.

The main run took 281.8 seconds, excluding analysis, on an RTX 5070 Laptop
with driver 595.99.02, CUDA compiler 13.1 and g++-13. All saved velocity
fields were finite and no broad numerical failure guard triggered.

| Main-run measurement | Value |
|---|---|
| Maximum logged integrated MAC divergence L2 | $1.55\times10^{-12}$ |
| Maximum logged cell-centred speed | 0.92349 lid-speed units |
| Maximum logged core-slip RMS | 0.000955 lid-speed units |
| Final core-slip RMS | 0.000377, or 0.0377% of lid speed |
| Maximum logged tether displacement | 0.005651 L |
| Final sphere centre | (0.500311, 0.502123, 0.500000) |

Core slip compares interpolated fluid velocity with body velocity at $r<R-h$.
The divergence check uses the solver's double-precision staggered face fields.
Low slip and divergence are useful numerical checks; they do not independently
establish correct pressure, force or coupled-body dynamics.

{{< figure src="/lid-driven-sphere/diagnostics.png" title="Sphere-centre displacement from the anchor, integrated MAC divergence, and core slip. The small motion reflects the restoring tether and evolving cavity flow." >}}

## Interpretation and limitations

The final flow view shows clockwise circulation around the sphere on the
central x–y plane, secondary recirculation to its right and in the lower-right
cavity region, and a fast near-lid layer. The sphere remains close to its anchor.
The Q surfaces highlight coherent rotation-dominated regions, especially
near the moving lid and corners. They provide no demonstration of turbulence.

This is a startup and circulation trial. The pilot ends at a different time,
so it cannot establish convergence of the final flow. Neither a settled state
nor physical/FSI benchmark accuracy has been established. Grid, time-step,
penalty/interface and wall-pressure checks remain necessary.

## Reproduce and inspect

Study source is committed in workspace revision `ae4484f`, using GPU solver
revision [`cd6f637`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/tree/cd6f637d3009e46f84d437136a669217003f72ea).
From `studies/lid-driven-sphere/` in the workspace:

```bash
/usr/local/cuda-13.1/bin/nvcc -std=c++17 -O3 -arch=sm_120 \
  -ccbin /usr/bin/g++-13 -fmad=true -I../../fdm-3d-v1-gpu/src \
  cavity_sphere.cu -o cavity_sphere
./cavity_sphere 64 2 0.001 runs/pilot64 100 1000
./cavity_sphere 96 10 0.001 runs/main96 250 1000
python3 analyse.py runs/main96
```

Arguments are grid size, final time, time step, output directory, frame
interval and cavity Reynolds number. Existing output directories are rejected.
Analysis requires NumPy, Matplotlib, Pillow and PyVista/VTK. The script supports
normal installations and the isolated package directory used in this workspace.

Raw snapshots are float32 cell-centred averages of the double-precision
staggered velocities, stored in z,y,x,component order. The frame index records
actual times and sphere centres. Analysis computes Q and vorticity with
PyVista, masks the diffuse solid for fluid-only Q, and exports a ParaView
`fluid.pvd` time series. The full fields remain local; the figures, scripts and
small diagnostic files are downloadable here.

- [Animation](/lid-driven-sphere/cavity-evolution.gif)
- [Velocity and streamlines](/lid-driven-sphere/cavity-flow.png) · [Q-criterion figure](/lid-driven-sphere/cavity-Q.png)
- [Main diagnostics](/lid-driven-sphere/main96-diagnostics.csv) · [Summary JSON](/lid-driven-sphere/summary.json) · [Main metadata](/lid-driven-sphere/main96-metadata.json) · [Frame index](/lid-driven-sphere/main96-frames.csv)
- [Pilot diagnostics](/lid-driven-sphere/pilot64-diagnostics.csv) · [Pilot metadata](/lid-driven-sphere/pilot64-metadata.json) · [Pilot frame index](/lid-driven-sphere/pilot64-frames.csv)
- [GPU driver](/lid-driven-sphere/cavity_sphere.cu) · [Analysis script](/lid-driven-sphere/analyse.py) · [Detailed run notes](/lid-driven-sphere/README.md)

Related: [3D GPU vortex decay and Q-criterion](/posts/gpu-vortex-decay-q-criterion/).
