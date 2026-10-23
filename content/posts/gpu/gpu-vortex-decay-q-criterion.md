---
title: "3D GPU vortex decay: Q-criterion, animations and boundary conditions"
description: "A 128³ no-slip-box simulation with actual time-resolved vortex surfaces, a PyVista Q-criterion figure, and explicit initial and boundary conditions."
date: 2026-10-16T00:00:00+08:00
academic: true
ShowToc: true
TocOpen: false
tags: ["CFD", "GPU", "vorticity", "Q-criterion"]
url: /posts/gpu-vortex-decay-q-criterion/
---

This experiment follows interacting three-dimensional vortices in a closed
unit cube using the existing GPU Navier–Stokes solver. It shows vortex
stretching, interaction and smaller-scale development over time. The initial
field contains smooth large structures; all subsequent frames come from the
numerical simulation.

**Status:** an exploratory demonstration of nonlinear 3D vortex breakdown and
turbulent-like decay. The grid comparison shows substantial sensitivity, so
quantitative turbulent statistics and DNS accuracy remain unverified.

## Watch the simulated flow

{{< figure src="/decaying-vortices/vortices3d.gif" title="3D evolution on the 128³ grid. Actual simulated Q=60 isosurfaces, coloured by vorticity magnitude on a fixed 0–150 scale; larger values saturate. There are 41 saved frames from nondimensional t=0 to 1.5. Playback speed is illustrative, not real time." >}}

{{< figure src="/decaying-vortices/q-criterion-pyvista.png" title="PyVista figure at t=0.75: Q=60 isosurface coloured by vorticity magnitude. Q was independently recomputed from the saved velocity; its interior relative L2 difference from the NumPy calculation is 6.66×10⁻⁸." >}}

{{< figure src="/decaying-vortices/vortex-evolution.gif" title="Mid-plane vorticity magnitude near z=0.5, using actual time-resolved velocity fields and a fixed colour scale. The shared colour range uses a robust percentile across frames and clips rare extremes. This is a slice through a three-dimensional flow." >}}

## Governing problem and scales

The nondimensional domain is $\Omega=[0,1]^3$. We solve incompressible flow,

$$
\partial_t\mathbf{u}+(\mathbf{u}\cdot\nabla)\mathbf{u}
=-\nabla p+\nu\nabla^2\mathbf{u},\qquad
\nabla\cdot\mathbf{u}=0,
$$

with kinematic pressure $p$, viscosity $\nu=0.0005$, and no body force.
The initial vector RMS speed is normalized to
$U_0=\sqrt{\langle u^2+v^2+w^2\rangle}=1$, where angle brackets denote a
volume average. With box length $L=1$, the initial box-scale Reynolds number is
$Re_0=U_0L/\nu=2000$. This uses the vector RMS, not the RMS of one component.
Time is nondimensionalized with $L/U_0$; the Reynolds number based on the
instantaneous RMS decreases as energy decays.

## Boundary conditions: all six faces

Every boundary is a stationary, impermeable, no-slip wall. All three velocity
components are prescribed to zero, for all times:

$$
\mathbf{u}|_{\partial\Omega}=\mathbf{0}.
$$

| Face | Normal velocity | Tangential velocities | Numerical pressure-correction BC |
|---|---|---|---|
| x=0 | u=0 | v=w=0 | $\partial_n\phi=0$ |
| x=1 | u=0 | v=w=0 | $\partial_n\phi=0$ |
| y=0 | v=0 | u=w=0 | $\partial_n\phi=0$ |
| y=1 | v=0 | u=w=0 | $\partial_n\phi=0$ |
| z=0 | w=0 | u=v=0 | $\partial_n\phi=0$ |
| z=1 | w=0 | u=v=0 | $\partial_n\phi=0$ |

There is no inlet, outlet, moving lid, periodic direction, immersed solid,
external forcing or turbulence closure. The only initial energy source is the
specified vortex field. Wall shear and viscosity influence the evolution;
this is a wall-bounded decay problem, not homogeneous periodic turbulence.

### Pressure treatment in the projection solver

The incremental projection solves a pressure correction $\phi$ with
homogeneous Neumann conditions on all faces. The solver removes the Poisson
RHS mean for compatibility and fixes the constant nullspace by subtracting
the mean correction. Pressure is updated incrementally, and the final pressure
mean is also removed. Initial pressure is zero. The implementation uses
homogeneous Neumann pressure ghost values as well.

These are the algorithm's numerical pressure conditions and gauge choice.
They should not be interpreted as an independently validated physical wall
pressure model. Pressure accuracy was not assessed in this experiment.

### How the velocity wall conditions are applied

The solver uses a staggered MAC grid: normal velocity components lie on the
boundary faces, while tangential components are offset from the wall. The
normal wall-face values are set to zero, and tangential Dirichlet conditions
enter the viscous solve and velocity ghost treatment. No open-boundary patches
or special wall-forcing models are enabled.

The largest logged normal wall velocity in the 128³ run is
$4.21\times10^{-13}$. The maximum logged integrated MAC divergence L2 norm is
$1.58\times10^{-12}$. These check impermeability and discrete incompressibility;
they do not independently establish wall-shear or pressure accuracy.

## Initial condition: reproducible interacting vortices

We define a vector potential $\mathbf{A}$ with a smooth wall envelope,

$$
E(x,y,z)=\sin^2(\pi x)\sin^2(\pi y)\sin^2(\pi z),
$$

$$
A_c=E\sum_{m=0}^{5}
\frac{\sin\!\left(\pi\mathbf{k}_m\cdot\mathbf{x}
+0.71(m+1)(c+1)+0.31c\right)}{m+1},\qquad c=0,1,2.
$$

The fixed mode vectors are
$(1,1,1),(2,1,1),(1,2,1),(1,1,2),(2,2,1),(1,2,2)$.
There is no runtime random seed. Component-dependent phases generate a
three-dimensional field rather than an extruded two-dimensional vortex.

Velocity is initialized as the **discrete edge-to-face curl**,
$\mathbf{u}_0=C\nabla_h\times\mathbf{A}$. The discrete MAC divergence of this
curl cancels to roundoff, avoiding the artificial startup divergence of an
arbitrarily sampled velocity field. The constant $C$ normalizes the
cell-centred vector RMS to one separately on each grid.

The sin-squared envelope makes the continuous potential and its first
derivatives vanish at the walls. Boundary samples of the potential are set
exactly to zero in the code; discrete normal boundary velocities therefore
vanish at initialization. The no-slip conditions are maintained during evolution.
The potential is used only for initialization, not to prescribe later frames.

## Runs and numerical settings

| Setting | Pilot | Main |
|---|---|---|
| Cells | 64³ | 128³ |
| Time step | 0.0005 | 0.00025 |
| Final time | 1 | 1.5 |
| Steps | 2,000 | 6,000 |
| Saved velocity frames | 21 | 41 |
| Frame interval | 0.05 | 0.0375 |
| Initial mean kinetic energy | 0.5 | 0.5 |

Both use double precision, FMA, backward-Euler viscosity and AB2
second-order-upwind convection. The configuration uses three Helmholtz
multigrid cycles and ten pressure cycles with three smoothing sweeps;
pressure means are reduced on the device. No turbulence model is added.
Upwind transport introduces numerical dissipation alongside physical viscosity.

The main run took about **245 seconds**, excluding post-processing, on an
RTX 5070 Laptop with driver 595.99.02, CUDA compiler 13.1 and g++-13.
The maximum logged cell-centred advective CFL is 0.2193. Velocity snapshots
are stored as float32 averages of the solver's double-precision staggered
velocities. Q and vorticity are derived from those cell-centred snapshots.

## What changed during the simulation?

{{< figure src="/decaying-vortices/vortex-evolution.png" title="Four mid-plane snapshots from the main simulation on a common colour scale. Initially broad structures are stretched into thinner sheets and vortical regions, followed by decay." >}}

{{< figure src="/decaying-vortices/statistics.png" title="Main-run energy, enstrophy and tapered spectral diagnostics. The nonperiodic-box spectrum is a windowed scale diagnostic; no inertial-range power law is asserted." >}}

| Main-run measurement | Result |
|---|---|
| Initial enstrophy | 66.8270 |
| Peak sampled enstrophy | 269.4643 at t=0.4875 |
| Peak / initial enstrophy | 4.03 |
| Mean interior enstrophy at that peak | 217.35, compared with 141.20 initially |
| Mean interior vortex stretching at that peak | +916.56 |
| Initial kinetic energy | 0.5 |
| Final kinetic energy at t=1.5 | 0.1047125 |
| Final spanwise velocity RMS | 0.26896 |

Enstrophy is $\tfrac12\langle|\nabla\times\mathbf{u}|^2\rangle$.
The interior statistics use the central sub-box
$[0.125,0.875]^3$. Positive mean interior vortex stretching and increased
interior enstrophy support nonlinear three-dimensional scale development;
the changes are not confined to the immediate wall region.

The fraction of the tapered spectral energy in shells $k\ge8$ increases
from $1.74\times10^{-7}$ initially to a sampled maximum of 0.0728 at $t=1.2$.
Here the velocity is multiplied by a separable sin-squared window before the
FFT because the domain is nonperiodic. This demonstrates scale broadening,
but the windowed spectrum is not a homogeneous-isotropic-turbulence benchmark.

### Resolution limits

At the common time $t=1$, kinetic energy is 0.1931552 on the pilot grid and
0.2071187 on the main grid, a **7.23% difference relative to the pilot**.
Peak sampled enstrophy is 160.84 and 269.46 respectively, a **67.5% increase**.
The time steps and peak sampling differ, so these are sensitivity measurements,
not a pure spatial convergence order.

The runs are not grid-converged. Vortex stretching, spectral broadening and
complicated Q surfaces support an exploratory turbulent-like decay
demonstration, but do not establish fully resolved turbulent dissipation,
a statistical inertial range, or benchmark-validated DNS. All logged energy
values decrease and saved velocity fields are finite; those checks address
numerical behaviour, not complete physical validation.

## Q-criterion and the PyVista figure

For $A=\nabla\mathbf{u}$, define
$S=(A+A^T)/2$ and $\Omega=(A-A^T)/2$. The plotted scalar is

$$
Q=\tfrac12\left(\|\Omega\|_F^2-\|S\|_F^2\right).
$$

Positive Q selects rotation-dominated regions. The displayed surface is
**Q=60**, with identical thresholds across frames. The value is a visualization
choice for this nondimensional case, not a universal turbulence threshold.

The static PyVista figure recomputes Q and vorticity directly from the
$t=0.75$ velocity with `compute_derivative`, then extracts the Q=60 surface.
Its interior relative L2 Q difference from the independent NumPy derivative
is $6.66\times10^{-8}$. The outer two cell layers are excluded because
boundary derivative stencils differ. This agreement checks the post-processing;
it is separate from validation of the flow solver.

## Reproduce and download

The driver uses GPU solver revision
[`cd6f637`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/tree/cd6f637d3009e46f84d437136a669217003f72ea).
From `studies/decaying-vortices/` in the workspace:

```bash
/usr/local/cuda-13.1/bin/nvcc -std=c++17 -O3 -arch=sm_120 \
  -ccbin /usr/bin/g++-13 -fmad=true -I../../fdm-3d-v1-gpu/src \
  vortex_box.cu -o vortex_box
./vortex_box 64 2000 0.0005 runs/pilot64 100 0.0005
./vortex_box 128 6000 0.00025 runs/main128 150 0.0005
```

Arguments are grid size, step count, time step, output directory, frame
interval and viscosity. Existing output directories are rejected to preserve
earlier results. The analysis script converts saved velocity frames into a
ParaView `fluid.pvd` time series and generates plots and diagnostics.
The full raw field series and restart checkpoints remain in the local study
directory; this page publishes figures, animations, derived tables and one
contour surface.

- [PyVista Q figure (PNG)](/decaying-vortices/q-criterion-pyvista.png) · [Q surface for ParaView (VTP, approximately 18 MB)](/decaying-vortices/q-criterion-pyvista.vtp)
- [3D Q animation](/decaying-vortices/vortices3d.gif) · [Vorticity-slice animation](/decaying-vortices/vortex-evolution.gif)
- [Main statistics (CSV)](/decaying-vortices/statistics.csv) · [Summary (JSON)](/decaying-vortices/summary.json) · [Pilot statistics (CSV)](/decaying-vortices/pilot64-statistics.csv)
- [Main solver diagnostics](/decaying-vortices/main128-diagnostics.csv) · [Pilot solver diagnostics](/decaying-vortices/pilot64-diagnostics.csv)
- [Main metadata](/decaying-vortices/main128-metadata.json) · [Pilot metadata](/decaying-vortices/pilot64-metadata.json)
- [GPU driver](/decaying-vortices/vortex_box.cu) · [Analysis script](/decaying-vortices/analyse.py) · [3D animation renderer](/decaying-vortices/render3d.py) · [PyVista plotting script](/decaying-vortices/plot_q_pyvista.py)

For analysis and animation, this machine uses ParaView's `pvpython`, with
NumPy, Matplotlib, Pillow and VTK. The static Q figure uses standalone Python
3.14 with PyVista 0.49.1 and VTK 9.7.1. The downloaded plotting script accepts
standard installations of those libraries; its additional local-package
search path is only needed for this workspace's isolated installation.

For comparison, the earlier
[small-grid flat-plate audit](/posts/flat-plate-gpu-verification/) investigated
mass balance in a weakly perturbed laminar boundary layer. The present study
changes the physical initial-value problem and boundary conditions rather
than relying on grid refinement to produce turbulence.
