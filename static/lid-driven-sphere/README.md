# Lid-driven cavity with a tethered rigid sphere

This is a data-independent rigid-sphere trial using the existing GPU fluid
solver. The repository's `demo/lid_cavity_sphere.cu` instead models an elastic
immersed sphere and needs `fdm-3d-v1-geometry/src/ibm/data/sphere`, which was absent
in this checkout. This study therefore reuses the previous analytic rigid-body
volume-penalty coupling; it does not claim to have run the elastic-sphere demo.

## Problem and boundary conditions

- Unit cube, fluid density 1, kinematic viscosity 0.001.
- Top lid at y=1 moves in +x, reaching speed 1. Thus Re_L=U_lid L/nu=1000.
- Lid speed ramps with s²(3-2s), s=clamp(t,0,1). All initial fluid velocities
  and pressure are zero. Times are nondimensional in L/U_lid.
- Top velocity: (U_lid(t),0,0). Other five walls: (0,0,0). All walls are
  impermeable and no-slip relative to their prescribed motion. The usual
  tangential discontinuity occurs where the moving lid meets stationary walls.
- Closed-domain pressure correction uses homogeneous Neumann conditions;
  its compatibility mean and constant nullspace are removed. Pressure is
  incrementally updated and zero-mean, with homogeneous Neumann ghost values.
  These are numerical projection conditions; physical pressure accuracy has
  not been independently validated.
- There are no pressure outlet patches, inlet, sponge or periodic boundaries.

## Sphere and tether

- Radius 0.18, diameter 0.36; anchor (0.5,0.5,0.5).
- Initial centre (0.505,0.5,0.5), initial velocity zero; density ratio 4.
- Rigid translation in three directions, fixed rotation, no deformation or gravity.
- Virtual centring spring/damper: F=-1*(X-X_anchor)-0.05*V. There is no meshed
  tether filament or its drag.
- Volume penalty f=200*chi*(V-u), with smoothstep interface of total width h.
  The reaction drives the body. Effective mass uses the same approximate
  fictitious-fluid inertia correction as the tethered-sphere through-flow trial:
  m_eff=4*(4*pi*R³/3)-sum(chi*h³), component by component. It assumes that
  the interior fluid follows the sphere and is not an independently validated
  added-mass model. The tether update is semi-implicit; fluid coupling is split.

The Reynolds number uses cavity length and lid speed. A diameter-based
number using the lid speed is 360, but the sphere sees a smaller and nonuniform
local flow. This is a baseline cavity/rigid-body experiment, not a turbulence
benchmark. Nonzero Q or 3D recirculation alone does not establish turbulence.

## Runs and reproducibility

| Run | Cells | dt | Final time | Frames |
|---|---|---|---|---|
| Pilot | 64³ | 0.001 | 2 | 21 |
| Main | 96³ | 0.001 | 10 | 41 |

Double precision, FMA, AB2 second-order upwind convection, backward-Euler
viscosity; 3 Helmholtz cycles, 10 pressure cycles, 3 smoothing sweeps, device
pressure mean reduction. dt*kappa=0.2. No turbulence closure is enabled.
The baseline source is GPU revision `cd6f637d3009e46f84d437136a669217003f72ea`.
Executed on RTX 5070 Laptop, driver 595.99.02, CUDA compiler 13.1, g++-13;
2026-10-16 (Asia/Shanghai).

From this directory:

```bash
/usr/local/cuda-13.1/bin/nvcc -std=c++17 -O3 -arch=sm_120 \
  -ccbin /usr/bin/g++-13 -fmad=true -I../../fdm-3d-v1-gpu/src \
  cavity_sphere.cu -o cavity_sphere
./cavity_sphere 64 2 0.001 runs/pilot64 100 1000
./cavity_sphere 96 10 0.001 runs/main96 250 1000
python3 analyse.py runs/main96
```

Arguments: N, final time, dt, output directory, frame interval, Re_L. Existing
output directories are rejected. Broad guards check finite velocity, MAC
divergence L2<=0.1, speed<=5, speed-based CFL<=0.4, tether displacement<=0.15L
and positive effective mass. They do not establish accuracy. No existing
solver source, shared build directory or other study outputs are modified.

The log retains `inlet_flux` and `outlet_flux` column names from the through-flow
driver; here they measure the closed z=0 and z=1 faces and should be near zero.
`fluid_transverse_rms` is the spatial RMS of (u,v) outside the diffuse sphere,
not temporal turbulence statistics. Core slip compares fluid velocity with
body velocity at r<R-h. Penalty reactions are not validated surface tractions.

Velocity snapshots are float32 cell-centred averages of the double-precision
staggered fields, in z,y,x,component order. `frames.csv` records actual times and
sphere centres. Analysis requires NumPy, Matplotlib, Pillow and PyVista/VTK;
it reuses the isolated package directory from the decaying-vortices study.

Open `runs/main96/visualization/fluid.pvd` in ParaView and Play. The frame series
includes velocity, speed, vorticity and Q. `cavity-evolution.gif` shows the
actual mid-plane speed evolution and sphere position. `cavity-flow.png` adds
instantaneous in-plane streamlines (not particle trajectories).
`cavity-Q.png` plots Q=0.5, excluding the diffuse solid, with the lid direction
marked. Q is a visualization diagnostic, not proof of turbulence.

Grid/interface/penalty refinement, longer integration and pressure/traction
checks remain necessary. The pilot ends earlier than the main case, so it
cannot establish convergence of the final flow or a settled cavity state.

## Measured result (2026-10-16)

The main case completed all 10,000 steps to t=10 in 281.8 seconds, saving
41 frames. All saved velocity frames were finite and no failure guard triggered.

| Quantity | Main-run measurement |
|---|---|
| Maximum logged integrated MAC divergence L2 | 1.55e-12 |
| Maximum logged cell-centred speed | 0.92349 U_lid |
| Maximum logged core-slip RMS | 0.000955 U_lid |
| Final core-slip RMS | 0.000377 U_lid (0.0377%) |
| Maximum logged tether displacement | 0.005651 L |
| Final sphere centre | (0.500311, 0.502123, 0.500000) |

The speed/streamline view shows a clockwise circulation around the sphere
on the central x-y plane, secondary recirculation near the right side of the
sphere and lower-right cavity region, and the fast moving-lid layer. The sphere
remains close to the spring anchor. The Q view contains coherent rotation-dominated
regions, including strong near-lid/corner structures; it does not demonstrate
turbulence. Sharp lid-edge boundary data can affect those gradients.

The pilot reached t=2 on a different grid and is a startup stability check,
not a final-time grid-convergence comparison. At t=10 neither steady state
nor physical/FSI benchmark accuracy has been established. The rigid sphere,
approximate penalty coupling and virtual tether differ from the repository's
unrun elastic-sphere demo.
