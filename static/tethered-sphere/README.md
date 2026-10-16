# Flow past a spring/damper-tethered rigid sphere

Exploratory trial using the existing GPU Navier–Stokes solver and a new isolated
rigid-body/volume-penalty driver. Existing GPU library headers and GLAMV builds
and outputs are unchanged. The earlier studies were committed in workspace
commit `8a18d92` before this simulation was started.

## Geometry, scales and boundary conditions

- Sphere diameter D=1, radius 0.5, reference inflow speed U=1, fluid density 1.
- Domain: [0,6] x [0,6] x [0,12]. Flow is in **positive z**.
- Reference sphere centre / virtual tether anchor: (3,3,3).
- Initial centre: (3.02,3,3), with zero translational velocity. The small x
  displacement seeds a departure from exact axial symmetry. The initial y
  symmetry is not explicitly broken; this can constrain early wake modes.
- Initial fluid velocity and pressure are zero. Inflow ramps from zero to one
  over t=0..1 using U(t)=s²(3-2s), s=clamp(t,0,1).
- At z=0: prescribed velocity (0,0,U(t)); pressure correction Neumann.
- On x=0,6 and y=0,6: prescribed coflow velocity (0,0,U(t)); pressure correction
  Neumann. These finite-distance Dirichlet boundaries approximate outer flow;
  they are not stationary side walls or periodic boundaries. Sphere area /
  cross-section area is about 2.18%; boundary influence still needs checking.
- At z=12: a full-plane pressure patch p=0, homogeneous Dirichlet correction,
  with the solver's PhysicalOpen velocity treatment (free tangential components
  and a normal divergence-free boundary reconstruction). This is implemented by
  a circular patch of radius 100 centred on the rectangular face, covering it.
- A downstream sponge acts over z=10..12: f_sponge=-sigma(z)(u-U(t)e_z),
  sigma=2*clamp((z-10)/2,0,1)². This force is excluded from the sphere reaction.
  The convection code still fills outer ghosts from its boundary policy;
  the outlet is therefore not a verified nonreflecting boundary. The sponge
  reduces the downstream disturbance before it reaches those ghosts.

Re_D=UD/nu=1000, nu=0.001. Times are in D/U. This is a wake trial, not a
benchmark-matched sphere DNS. Published turbulent sphere-wake studies often
use Re=3700 or higher; wake unsteadiness and nonzero vorticity here do not by
themselves establish turbulence.

## What “tethered sphere” means here

The sphere is rigid and translates in x, y and z. Rotation is held fixed and
no deformation, gravity, contact, or physical tether-filament flow is modelled.
The tether is an ideal three-component centring spring/damper:

F_tether = -5*(X-X_anchor) - 0.4*V.

The virtual anchor is the reference centre, so this is a restoring-force
model, not an explicitly meshed string attached to an external support.
The nominal solid density is 4 and nominal solid mass is 4*pi/6.

Inside the sphere, the fluid is coupled toward the rigid-body velocity with
f_penalty = 100*chi*(V-u). chi is one inside R-h/2, zero outside R+h/2, and
a smoothstep between. The force is evaluated on each component's staggered
faces. The opposite volume-integrated penalty force drives the body.

To approximately account for fictitious fluid inside the volume-penalty body,
the translational update uses component-wise effective mass
m_eff = rho_s*(pi/6) - sum(chi_component*h³).
This assumes that the interior fluid follows the body. It is an approximate
inertia correction, not a measured hydrodynamic added-mass model. Finite slip,
diffuse interfaces and split coupling introduce error. The logged `reaction_*`
values are the penalty reaction, not an independently validated surface
traction or drag coefficient.

Spring and damper are integrated with a semi-implicit velocity/position update;
fluid forcing uses the preceding body state. All coupling is bidirectional:
fluid velocity determines reaction, reaction changes the sphere position, and
the new position changes the next penalty mask. With dt=0.002, dt*kappa=0.2.

## Runs and numerical settings

| Run | Cells | Cells per D | dt | Final time | Frames |
|---|---|---|---|---|---|
| Pilot | 48 x 48 x 96 | 8 | 0.002 | 2 | 11 |
| Main | 96 x 96 x 192 | 16 | 0.002 | 15 | 51 |

Double precision, FMA, AB2 second-order upwind convection, backward-Euler
viscosity; 3 Helmholtz cycles, 10 pressure cycles, 3 pressure smoothing sweeps;
device mean reduction. No turbulence closure is used. Sixteen cells across
the diameter do not resolve a Re=1000 sphere boundary layer sufficiently for
a DNS claim. Interface width, penalty rate, boundary distance, time step and
grid sensitivity remain to be studied.

Solver revision: `cd6f637d3009e46f84d437136a669217003f72ea`.
Hardware: RTX 5070 Laptop, driver 595.99.02. CUDA compiler 13.1, g++-13.
Study date: 2026-10-16 (Asia/Shanghai).

## Reproduce

```bash
/usr/local/cuda-13.1/bin/nvcc -std=c++17 -O3 -arch=sm_120 \
  -ccbin /usr/bin/g++-13 -fmad=true -I../../fdm-3d-v1-gpu/src \
  sphere_flow.cu -o sphere_flow
./sphere_flow 8 2 0.002 runs/pilot8 100 1000
./sphere_flow 16 15 0.002 runs/main16 150 1000
python3 analyse.py runs/main16
```

Run from this study directory. Arguments: cells per diameter, final time, dt,
output directory, frame interval, Re_D. Existing output directories are
rejected. `analyse.py` uses the standalone NumPy/Matplotlib/Pillow/PyVista/VTK
installation in the sibling decaying-vortices study; normal Python
installations of those packages also work.

The driver logs finite-velocity checks, integrated MAC divergence, sphere
position and velocity, penalty reaction, inlet/outlet flux, inner-core slip,
and wake transverse RMS. Guards stop at divergence L2>0.1, speed>5, the simple
speed-based CFL>0.4, or tether displacement>0.4D. They are broad failure guards,
not accuracy acceptance criteria. The core-slip statistic samples r<R-h and
compares cell-centred fluid velocity with body velocity. Wake RMS samples
z=Xz+0.75..Xz+4, |x-Xx|<1, |y-Xy|<1; it measures spatial crossflow, not temporal
turbulence fluctuations.

Raw frames contain float32 interpolated cell-centred velocity in z,y,x,component
order. The solver runs in double precision. Each frame records the actual
centre in `frames.csv`. Post-processing computes Q and vorticity with PyVista,
masks the diffuse solid for fluid-only Q, exports a ParaView `fluid.pvd`, and
plots the wake animation and sphere motion. The final Q=0.5 surface is selected
downstream of the sphere (z>Xz+0.6, z<9.8); threshold and selection are visualization
choices, not turbulence tests. Moving-solid shear and imposed startup transients
must not be mistaken for turbulent wake development.

## Measured trial results (2026-10-16)

The main run completed all 7500 steps to t=15 in 330.4 seconds, saving 51
velocity frames. No failure guard triggered and all saved velocity frames were
finite. The resulting fields show an unsteady wake with shed vortical structures.

| Main-run quantity | Measured value |
|---|---|
| Maximum logged integrated MAC divergence L2 | 9.86e-14 |
| Maximum logged speed | 1.39672 |
| Maximum logged tether displacement | 0.25441 D |
| Final centre | (2.98099, 3.00000, 3.07303) |
| Maximum logged core-slip RMS | 0.01672 U |
| Final core-slip RMS | 0.00785 U |
| Final spatial wake transverse-speed RMS | 0.25865 U |
| Temporal vector-velocity RMS in the fixed wake box | 0.17109 U |

The temporal statistic uses 26 snapshots over t=7.5..15 and the fixed region
2<x<4, 2<y<4, 4<z<8. It subtracts each point's sample mean and then averages
the sum of component variances over that region. It includes coherent wake
shedding, tether motion and possible continuing mean evolution; it is not a
converged turbulent fluctuation statistic. The initial y symmetry is largely
retained, which may suppress some wake modes.

The inlet and outlet flux are both 36 after the ramp at the printed precision
of the solver log. The reported zero relative difference is limited by that
precision and does not assert exact floating-point equality of unrounded
flux integrals. Small divergence does not establish correct surface traction
or accurate rigid-body coupling.

The coarse trial ended at t=2 and cannot be used to establish convergence of
the later unsteady wake. This experiment demonstrates a moving, tethered sphere
and wake shedding, with approximate penalty coupling. Turbulence and DNS-level
accuracy are not established by the current resolution, time window or initial
symmetry. Higher resolution, interface/penalty refinement, longer averaging,
boundary-distance tests and controlled three-dimensional perturbations are
needed before making stronger claims.

Open `runs/main16/visualization/wake-evolution.gif` for the actual-frame animation,
`wake-Q.png` for the PyVista Q=0.5 wake figure, or `fluid.pvd` in ParaView for
the complete 51-frame fluid time series. `diagnostics.png` shows tether motion,
coupling reaction and numerical diagnostics, and `summary.json` records metrics.

## References motivating follow-up validation

- [Flow dynamics in the turbulent wake of a sphere at sub-critical Reynolds
  numbers](https://www.sciencedirect.com/science/article/pii/S0045793012000965)
  studies Re=3700 and 10000; it is not a quantitative reference for this setup.
- [Improving convergence of volume penalised fluid-solid interactions](https://arxiv.org/abs/1903.11914)
  discusses penalty-model and discretization errors, which require separate
  assessment from Navier–Stokes residual convergence.
