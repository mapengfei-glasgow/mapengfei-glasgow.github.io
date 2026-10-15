---
title: "Checking a small-grid GPU flat-plate simulation: stability, mass balance and refinement"
description: "A three-run audit separates a boundary-flux mismatch from pressure-projection error, and explains why a stable 3D run is not yet validated turbulence."
date: 2026-10-15
academic: true
ShowToc: true
TocOpen: false
tags: ["CFD", "GPU", "verification", "flat plate"]
---

A 32 × 32 × 16 flat-plate calculation completed without NaNs. That was a useful
starting point, but it did not establish that the flow was accurate. This note
checks the saved staggered fields, repeats the calculation on a finer grid and
with half the time step, and states what these tests actually establish.

**Finding:** the three runs are stable over one flow-through time, and sampled
velocity profiles are insensitive to the tested refinement. The persistent
divergence is dominated by a small imbalance in prescribed boundary fluxes.
The case remains a finite-span laminar smoke test with a weak 3D perturbation;
it is not a turbulent DNS, LES, or a completed flat-plate validation.

## The problem actually solved

The domain is $1\times0.2\times0.2$, with $U_\infty=1$ and kinematic viscosity
$\nu=0.001$. Thus $Re_L=1000$. A stationary no-slip plate is at $y=0$.
The inlet, outlet, top and spanwise planes have prescribed velocities. In
particular, the spanwise boundaries are **not periodic** and the outlet is
**not an open outflow**.

The initial and outer-boundary velocity profile is

$$
a(x)=\frac{1}{2\sqrt{\nu(x+0.25)}},\qquad
u=\operatorname{erf}(ay),\qquad
v=\frac{1-e^{-a^2y^2}}{2a\sqrt{\pi}(x+0.25)},\qquad w=0.
$$

This profile is divergence-free in the continuum: $\partial_xu+\partial_yv=0$.
It is an approximation for initialization and boundary data, **not an exact
Navier–Stokes solution**. A virtual origin at $x=-0.25$ avoids the leading-edge
singularity. A small cross-plane perturbation is added initially through
$v'=\partial_z\psi'$ and $w'=-\partial_y\psi'$, where

$$
\psi'=\frac{0.001L_y}{\pi}
\sin^2\left(\frac{\pi x}{L_x}\right)
\sin^2\left(\frac{\pi y}{L_y}\right)
\sin^2\left(\frac{\pi z}{L_z}\right).
$$

The perturbation vanishes at the boundaries. There is no body forcing,
turbulence closure, sustained turbulent inflow, or time-averaged turbulence
measurement. The calculation uses the GPU incremental projection solver,
double precision, FMA, second-order upwind convection and backward-Euler
viscosity. Four Helmholtz multigrid cycles and twenty pressure cycles are used
per step, with three pressure smoothing sweeps.

## Three controlled runs

All runs stop at the same nondimensional time $t=1$, one nominal domain
flow-through time. They use the same domain, viscosity and initial condition.

| Run | Cells | Time step | Steps | Final maximum speed | Divergence integrated L2 |
|---|---|---|---|---|---|
| Coarse | 32 × 32 × 16 | 0.001 | 1,000 | 1.047688 | $3.48728\times10^{-5}$ |
| Fine | 64 × 64 × 32 | 0.001 | 1,000 | 1.047750 | $8.70439\times10^{-6}$ |
| Half time step | 32 × 32 × 16 | 0.0005 | 2,000 | 1.047695 | $3.48723\times10^{-5}$ |

All final staggered velocity and pressure arrays contain finite values.
The driver checks finite cell-centred velocity/pressure and broad stability
limits at recorded steps. Those limits are smoke-test guards, not accuracy
criteria. The original 32-grid output was retained; these checks used separate
run directories and full-precision staggered field dumps.

{{< figure src="/flat-plate-validation/velocity-profiles.png" title="Figure 1. Coarse-grid streamwise velocity near the centre span at t=1, and near-centre-span profiles at x=0.5 for all three runs. The initial boundary layer was already present; this image alone does not demonstrate development from a uniform inflow or transition to turbulence." >}}

## Mass balance identifies the divergence floor

For each cell we independently reconstruct the MAC-grid divergence from its
six face velocities. We also integrate outward flux on all six domain faces.
These satisfy the discrete divergence theorem to an absolute discrepancy below
$10^{-14}$:

$$
\sum_{\partial\Omega}Q_{\rm outward}
=\sum_{\rm cells}(\nabla_h\cdot\mathbf{u})\,\Delta V.
$$

| Quantity at t=1 | Coarse | Fine | Half time step |
|---|---|---|---|
| Net outward flux | $-6.97447\times10^{-6}$ | $-1.73931\times10^{-6}$ | $-6.97444\times10^{-6}$ |
| Absolute net flux / inlet flux magnitude | 0.01914% | 0.004774% | 0.01914% |
| Mean divergence | $-1.74362\times10^{-4}$ | $-4.34828\times10^{-5}$ | $-1.74361\times10^{-4}$ |
| Mean-subtracted divergence integrated L2 | $1.79268\times10^{-7}$ | $3.69195\times10^{-7}$ | $8.96724\times10^{-8}$ |
| Maximum normal-velocity boundary error | $1.88244\times10^{-8}$ | $3.61283\times10^{-8}$ | $9.41206\times10^{-9}$ |

The last row compares the normal face velocity with its prescribed value on
each boundary, including zero wall-normal velocity at the plate. It does not
independently verify tangential wall velocity or wall shear.

For the coarse run, the outward fluxes through inlet, outlet and top are
approximately $-0.03644339$, $+0.03202649$ and $+0.004409927$.
Bottom and spanwise net fluxes are near zero. The prescribed top velocity
therefore carries an important part of the flux balance; considering only inlet
and outlet would misdiagnose this case.

The domain volume is $0.04$. A uniform divergence equal to the measured mean
alone gives an integrated L2 norm $|\overline{\nabla_h\cdot u}|\sqrt{0.04}$,
almost the entire reported divergence. The pressure-correction problem has
homogeneous Neumann conditions, and its incompatible RHS mean is removed.
That projection cannot eliminate net prescribed boundary flux. Sampling the
continuum divergence-free profile on the discrete boundary faces leaves a
small quadrature mismatch.

This diagnosis is supported by three observations: the independent face-flux
balance matches volume-integrated divergence; normal-boundary errors are tiny;
and halving the grid spacing reduces total divergence by **4.006**, whereas
halving the time step barely changes it. The nonuniform residual is much smaller
but grows on the fine grid with the fixed multigrid cycle count. Solver-tolerance
convergence remains to be tested; the total divergence alone hides that trend.

{{< figure src="/flat-plate-validation/energy-mass-balance.png" title="Figure 2. Volume-mean kinetic energy over time and total versus mean-subtracted divergence. Energy is still evolving at t=1. The divergence norm is dominated by its mean, which is set by the net boundary flux." >}}

## How much do the profiles change?

For the quantitative grid comparison, velocity is sampled on common x faces.
The two central spanwise samples are averaged, and pairs of fine wall-normal
cells are averaged onto coarse cells. The RMS differences below are normalized
by $U_\infty=1$ and averaged uniformly over the sampled height.

| Station | Coarse–fine profile RMS difference | Coarse–half-time-step profile RMS difference |
|---|---|---|
| x=0.5 | $2.99809\times10^{-4}$ (0.02998%) | $2.87048\times10^{-6}$ (0.0002870%) |
| x=0.75 | $2.11712\times10^{-4}$ (0.02117%) | $9.56748\times10^{-6}$ (0.0009567%) |

The profiles agree closely for the tested discretizations. Two grids do not
establish an asymptotic convergence order or a continuum error estimate.
Moreover, convergence to the finite-box problem does not establish agreement
with an external flat-plate benchmark.

## Why this is not yet a Blasius or turbulence validation

A first-cell wall-shear estimate at $x=0.5$ gives
$C_f\approx0.03405$ on the coarse grid and $0.03415$ on the fine grid, using
$C_f\approx4\nu u(y=\Delta y/2)/(U_\infty^2\Delta y)$ and the imposed zero wall
velocity. This is a one-cell gradient estimate, not a converged shear calculation.

For context, the Blasius relation is $C_f=0.664/\sqrt{Re_x}$.
Using the same virtual-origin distance, $Re_x=(0.5+0.25)/0.001=750$, gives
$C_f\approx0.02425$. The fine-grid estimate is about **41% larger**. This is
not a like-for-like benchmark error: our inflow is an erf approximation, the
outlet and side velocities are prescribed, the domain is finite, and the
solution is still transient. Nevertheless, the discrepancy rules out claiming
Blasius validation from the present evidence. NASA provides a
[laminar flat-plate validation case and Blasius data](https://www.grc.nasa.gov/www/wind/valid/fplam/fplam.html);
the skin-friction relation also appears in
[NASA's LAVA flat-plate comparison](https://ntrs.nasa.gov/api/citations/20140008915/downloads/20140008915.pdf).

The coarse-run mean kinetic energy changes by $6.85\times10^{-5}$ between
$t=0.95$ and $1.00$. We have not demonstrated a steady state. Nonzero spanwise
velocity is also not evidence of turbulence: the initial condition deliberately
contains a 3D perturbation, and the finite-span boundaries can generate 3D effects.

The [SU2 tutorial](https://su2code.github.io/tutorials/Inc_Turbulent_Flat_Plate/)
solves steady 2D RANS with Spalart–Allmaras. The
[KTH DNS database](https://www.mech.kth.se/~pschlatt/DATA/) supplies turbulent
boundary-layer statistics starting at $Re_\theta=670$. Neither is reproduced by
this $Re_L=1000$ smoke test; these Reynolds numbers use different length scales.

## What is established, and the next experiment

This audit establishes finite fields over the tested interval, close agreement
between two sampled profile discretizations, and an independently accounted-for
mass-balance error. It does not establish exact mass conservation, benchmark
accuracy, long-time stability, or turbulent statistics.

The next experiment should make boundary flux discretely compatible, test
pressure/Helmholtz tolerances, and use benchmark-consistent laminar inflow and
outer boundaries. It should then check settling, a third grid, wall shear and
velocity profiles against a Blasius reference. A turbulent boundary-layer study
additionally needs verified spanwise periodicity, an appropriate outflow and
turbulent inflow or tripping, sufficient wall resolution, and statistical sampling.

## Reproduce and inspect

Measured on an RTX 5070 Laptop with driver 595.99.02, CUDA compiler 13.1 and
g++-13. Solver revision:
[`cd6f637`](https://github.com/mapengfei-glasgow/fdm-3d-v1-gpu/tree/cd6f637d3009e46f84d437136a669217003f72ea).

From `studies/flat-plate-small-grid/` in the workspace:

```bash
/usr/local/cuda-13.1/bin/nvcc -std=c++17 -O3 -arch=sm_120 \
  -ccbin /usr/bin/g++-13 -fmad=true -I../../fdm-3d-v1-gpu/src \
  flat_plate.cu -o flat_plate
./flat_plate 32 1000 runs/n32_dt1e-3
./flat_plate 64 1000 runs/n64_dt1e-3
./flat_plate 32 2000 runs/n32_dt5e-4 0.0005
```

The four `.bin` files in each run contain native little-endian float64
staggered arrays including ghosts, in k–j–i storage order. `metadata.txt` records
grid counts, domain lengths, viscosity, time step and step count. The analysis
script documents the array shapes and reconstructs all reported conservation
quantities directly. The scripts and small derived data are provided here;
the full raw run arrays remain in the local study directory.

- [GPU study driver](/flat-plate-validation/flat_plate.cu)
- [Independent analysis and figure script](/flat-plate-validation/analyse.py)
- [Numerical summary (JSON)](/flat-plate-validation/summary.json)
- [Metrics (CSV)](/flat-plate-validation/metrics.csv)
- [Coarse diagnostics](/flat-plate-validation/n32_dt1e-3-diagnostics.csv) · [Fine diagnostics](/flat-plate-validation/n64_dt1e-3-diagnostics.csv) · [Half-time-step diagnostics](/flat-plate-validation/n32_dt5e-4-diagnostics.csv)
- [Coarse profiles](/flat-plate-validation/n32_dt1e-3-profile.csv) · [Fine profiles](/flat-plate-validation/n64_dt1e-3-profile.csv) · [Half-time-step profiles](/flat-plate-validation/n32_dt5e-4-profile.csv)

The analysis requires NumPy and Matplotlib. On this machine these are available
in ParaView's Python environment: run `pvpython analyse.py` from the study
directory. For a standalone system Python installation, Ubuntu provides
`python3-numpy` and `python3-matplotlib` through `apt`.
