---
title: "AFSI"
description: "AFSI — an automated fluid–structure interaction solver on FEniCSx: demo configurations, run parameters and measured results."
date: 2026-09-12
---

**AFSI** (*Automated Fluid–Structure Interaction Solver*) couples an
incompressible Navier–Stokes solver on a fixed Cartesian grid to a Lagrangian
solid through the **immersed boundary method**, inside the
[FEniCSx](https://fenicsproject.org/) finite-element framework. Because FEniCSx
supplies the automatic assembly of the discrete equations, the solver can drive
nonlinear solids with large deformations and large displacements without
hand-written element routines.

**Authors:** Pengfei Ma, Xuan Wang · **Licence:** GPLv3

**Code:** [github.com/npuheart/afsi](https://github.com/npuheart/afsi) · **Requires:** FEniCSx 0.10.0

**Cite:** Ma, P., Cai, L., Wang, X., Gao, H. *AFSI: Automated Fluid-Structure Interaction Solver Development for Nonlinear Solid Mechanics.* arXiv:2509.00014 (2025).

## Verification demos

The pages below document individual demos in detail: the full parameter set, the
boundary conditions, the commands that produced the numbers, and the measured
results — including the parts that do **not** match the reference solution, with
the diagnosed cause.

| Demo | Problem | What it establishes |
|---|---|---|
| [`demo_423`](/afsi/demo-423/) | Static equilibrium of an immersed anisotropic annular solid in a driven cavity | Analytic pressure field reproduced by the immersed coupling; quadrilateral vertex-ordering pitfall |
| [`demo_424`](/afsi/demo_424/) | Tethered aorta in a box — patent and occluded variants | Pressure-driven open boundaries, an immersed sealing membrane, a mesh-refinement study, and a diagnosed defect in the IPCS solver |

Both write their raw results to `plot/` as XDMF/HDF5 plus a `verify.json`
summary; the figures on those pages were rendered from those files.

## Demo catalogue

The repository ships 14 demos (plus one reserved directory), each with a
`generate_mesh.py` (solid mesh) and a `main.py` (solve). The list below is the
catalogue from `afsic/demo/readme.md`.

### Two-dimensional

| Demo | Problem |
|---|---|
| `demo_336` | Disc carried by a lid-driven cavity flow (immersed boundary vs multi-direct forcing) |
| `demo_339` | Flow past a cylinder, four ways: no cylinder / body-fitted mesh / IBFE / multi-direct forcing |
| `demo_340` | Ideal 2-D valve, fibre-reinforced (FRH) leaflets at 45° / 60° / 75°, physiological sinusoidal inlet |
| `demo_343` | Discs advected through an ideal 2-D valve (lower leaflet 10× stiffer), with a `CIRCLE=0` control |
| `demo_400` | 2-D turtle: head and tail fixed, periodic follower pressure along the spine, limbs flapping |
| `demo_402` | Turek FSI2 benchmark — channel with a cylinder and a flexible flag (`SVK`, Re = 100) |
| `demo_421` | Fish swimming — a FEniCSx port of DFIBMFoam's `CircularFishSwimming` |
| `demo_423` | Immersed anisotropic annulus at static equilibrium, verified against the analytic pressure |
| `demo_424` | Tethered planar aorta — patent and occluded (sealed-membrane) verification cases |

### Three-dimensional

| Demo | Problem |
|---|---|
| `demo_337` | Ideal left ventricle, diastolic filling and systolic contraction (IB-FE, passive Neo-Hookean) |
| `demo_341` | Sphere in a 3-D lid-driven cavity; mid-line interpolation at t = 1 s, pure NS vs FSI |
| `demo_401` | Sperm cell (spherical head + three-segment flagellum) solid geometry and mesh |
| `demo_403` | Beam in cross flow (Tuković 2018 §4.5), Re = 40, symmetric half domain, plate clamped at the base |
| `demo_405` | 3-D vessel wall FSI (wedge/tetrahedral mesh) with a valve, sinusoidal inflow |

> `demo_422` is an empty placeholder directory.

## Running a demo

AFSI needs FEniCSx 0.10.0 and an editable install of the `afsic` package:

```bash
# environment (see install.md in the repository)
sudo install/install_env.sh
source install/activate_dolfinx
install/install_dolfinx
cd afsic && pip install .

# then, for any demo
cd afsic/demo/demo_424
CASE=open NY=45 python generate_mesh.py && CASE=open NY=45 python main.py
```

Most demos accept environment-variable overrides (`STEPS`, `NY`, `DT`,
`SOLVER`, `CIRCLE`, `GRID`, …) so a case can be shortened for a quick check;
each demo page lists the ones that matter and the wall-clock cost of the runs
behind its numbers.
