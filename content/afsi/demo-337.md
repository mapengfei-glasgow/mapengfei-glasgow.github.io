---
title: "337: Idealised Left Ventricle"
description: "A passively loaded left ventricle, compared against pulse-fenicsx and IBAMR."
date: 2026-09-12
weight: 337
academic: true
demo_id: demo_337
category: Application
dimension: 3D
solid_model: "neo-Hookean wall (E = 10⁴, ν = 0.3); legacy variants add Guccione fibres and active contraction"
coupling: "immersed boundary (`IBMesh3D` / `IBInterpolation3D`) + base-ring penalty"
reference: "pulse-fenicsx and IBAMR displacements (`data/reference/`)"
status: Partial
---

## 1. Introduction

A passive left-ventricle ellipsoid immersed in a $\mathrm{5 \times 5 \times 5}$
fluid box, loaded by a physiological endocardial pressure waveform. The wall is a
neo-Hookean solid whose internal force is spread back onto the fluid through
`IBMesh3D`/`IBInterpolation3D`; a penalty on the base ring restrains the valve
plane. The demo exists to compare AFSI's mid-wall displacement against
`pulse-fenicsx` and IBAMR, and it carries the MPI scaling study for the
$32^3$ and $64^3$ grids.

Legacy variants (`fsi_paralell*.py`) add fibre families (Guccione) and active
contraction; the readme labels them as reference versions.

## 2. Problem description

### 2.1 Geometry

{{< figure src="/afsi/demo337-setup.png" title="Figure 1. The idealised ventricle: endocardial and epicardial ellipsoids, the penalty-held base ring, and the endocardial pressure load. Drawn from the radii recorded in the demo." >}}

The ventricle is an ellipsoid pair (endocardium and epicardium) standing in the
box, with semi-axes $r_{\text{short}} = 7.0$ / $10.0$ and
$r_{\text{long}} = 17.0$ / $20.0$; the base ring is held by a penalty.

### 2.2 Governing equations

{{< color "red" >}}TODO: governing equations — incompressible Navier–Stokes, the neo-Hookean wall constitution, the endocardial pressure traction and the IB coupling terms (see the symbol table page).{{< /color >}}

### 2.3 Boundary and initial conditions

The endocardium carries the physiological pressure waveform
($8\,\mathrm{mmHg}$ diastolic, $110\,\mathrm{mmHg}$ systolic); the base ring is
restrained by the penalty. There are **no environment-variable overrides** in this
demo; the parameters live in `configuration.py`.

### 2.4 Physical parameters

<p class="tcaption">Table 1. Main-run parameters (`configuration.py`, consumed by `main.py`).</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid box | `Lx`, `Ly`, `Lz` | $5.0$, $5.0$, $5.0$ |
| Fluid density / viscosity | `rho`, `mu` | $1.0$ / $0.01$ |
| Solid model | `NeoHookeanMaterial` | $E = 1.0\times10^{4}$, $\nu = 0.3$ (the config's `mu_s` $= 0.1$ is **not** used) |
| Base-ring penalty | `beta` | $5\times10^{6}$ |
| Endocardial pressure | `diastole_pressure`, `systole_pressure` | $8\,\mathrm{mmHg}$ / $110\,\mathrm{mmHg}$ |
| LV mesh radii | `r_short_endo` … | $7.0$ / $10.0$ short, $17.0$ / $20.0$ long |

{{< color "red" >}}TODO: dimensionless numbers and the physiological scaling (cycle time, Reynolds number) if the case is to be reported as a model problem.{{< /color >}}

## 3. Numerical setup

The main run is fixed at $32^3$ hexahedral fluid cells with
$\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ velocity / force / pressure spaces
and $100$ steps of $\Delta t = 1/1000\,\mathrm{s}$ ($T = 0.1\,\mathrm{s}$), driven
by `ChorinSolver`; the grid is changed by editing `Nx`…`Nz` in
`configuration.py`. The ventricular mesh and the `pulse-fenicsx` reference
displacements are produced outside AFSI, in a Docker container
(`data/plot/docker-compose.yml`, `ghcr.io/finsberg/fenicsx-pulse:v0.4.1`); see §6.

<p class="tcaption">Table 2. Numerical setup of the main run.</p>

| Quantity | Code name | Value |
|---|---|---|
| Fluid cells | `Nx`, `Ny`, `Nz` | $32$, $32$, $32$ hexahedra |
| Velocity / force / pressure spaces | `velocity_order` … | $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ |
| Time step / end time | `dt`, `T` | $1/1000\,\mathrm{s}$ / $0.1\,\mathrm{s}$ ($100$ steps) |
| Solver | `ChorinSolver` | fixed at $32^3$ unless `Nx`… are edited |

## 4. Results

### 4.1 Quantities of interest

The quantities of interest are the mid-wall displacement at end-diastole and
end-systole, compared against the `pulse-fenicsx` and IBAMR reference series
($58$ rows each), and the MPI strong-scaling metrics (wall time and speed-up at
fixed problem size) on the $32^3$ and $64^3$ grids.

### 4.2 Comparison with the reference solvers

{{< figure src="/afsi/demo337-results.png" title="Figure 2. Archived data: strong scaling from `data/32x32x32.csv` and `data/64x64x64.csv`, and the end-diastolic mid-wall line against the `pulse-fenicsx` reference, plotted the way `plot_diastole.py` does." >}}

The archived reference series are the four $58$-row displacement files in
`data/reference/` and the end-diastolic mid-wall location
(`ideal_middle_wall.txt`). The comparison figures the readme describes
(`diastole_plot.png`, `systole_plot.png`) are **not** in the repository, and
neither is the $58$-row AFSI displacement for the systole case — the quantitative
comparison is therefore incomplete as archived.

{{< color "red" >}}TODO: the comparison table against Land et al. (2015) Problem 2 and against pulse-fenicsx / IBAMR — apex displacement and end-face positions, mean and amplitude per cycle.{{< /color >}}

| Quantity | AFSI | Reference | rel. err. |
| --- | --- | --- | --- |
| Apex displacement (diastole) |  |  |  |
| Apex displacement (systole) |  |  |  |
| End-face position (diastole) |  |  |  |
| End-face position (systole) |  |  |  |

### 4.3 Convergence study

{{< color "red" >}}TODO: grid and time-step sensitivity — only strong scaling at fixed problem size was recorded; no refinement study exists.{{< /color >}}

### 4.4 MPI strong scaling

The archived scaling numbers are (wall time per run):

| Grid | Processes | Wall time | Speed-up |
|---|---|---|---|
| $32^3$ | $1 \to 160$ | $1278.7\,\mathrm{s} \to 61.8\,\mathrm{s}$ | $21.1$ |
| $64^3$ | $1 \to 160$ | — | $50.1$ |

Source: `data/32x32x32.csv`, `data/64x64x64.csv`. No field figures are archived for
this demo.

## 5. Discussion and limitations

* `mu_s` $= 0.1$ is set in the configuration and quoted in the readme, but
  `main.py` never reads it — the solid is `NeoHookeanMaterial()` with its
  defaults $E = 10^{4}$, $\nu = 0.3$.
* `calculate_pressure_linear` returns only the systolic ramp for
  $t < t_{cycle} = 0.8\,\mathrm{s}$, so for $T = 0.1\,\mathrm{s}$ the
  $8\,\mathrm{mmHg}$ diastolic load passed to it never enters the value applied.
* `data/mesh/`, `data/results/` and `data/figures/` do not exist, so the demo
  cannot run or plot as shipped without regenerating the mesh and the references
  through Docker.
* The legacy scripts still call `create_vector(L_hat)`, removed in dolfinx 0.10
  (only `main.py` is fixed), and contain hard-coded absolute paths from the
  original machines.
* `GuccioneMaterial` reads `params["kappa"]`, which its `default_parameters()`
  does not define, so a bare instantiation raises `KeyError`; every call site
  passes it explicitly.
* The drivers call SwanLab on import and per output step, and the timing variant
  queries an HTTPS counter — offline runs need the stubs.

## 6. Reproducibility

<p class="tcaption">Table 3. Files in the demo.</p>

| File | Role |
|---|---|
| `configuration.py` | All main-run parameters, `num_steps`, output paths |
| `main.py` | 3-D IB-FE driver: Chorin solver, neo-Hookean LV, pressure traction on the endocardium, `metrics.csv` |
| `NeoHookean.py`, `Guccione.py`, `HolzapfelOgden.py` | Constitutive laws (only neo-Hookean is used by `main.py`) |
| `PressureEndo.py` | Endocardial pressure and active-tension waveforms |
| `read_mesh.py`, `ReadFibers.py`, `test_fibers.py` | Mesh transform, fibre/sheet readers, fibre-field diagnostic |
| `fsi_paralell*.py` | Legacy variants: plain, fibres, active contraction, timing ($64^3$) |
| `data/32x32x32.csv`, `data/64x64x64.csv` | MPI strong-scaling measurements |
| `data/reference/` | `ideal_middle_wall.txt` and the `pulse-fenicsx` diastole/systole displacements ($58$ rows each) |
| `data/plot/` | Mesh generation, `pulse-fenicsx` benchmarks, plotting scripts, Docker compose |

```bash
conda activate afsi-dolfinx-v1
cd afsic/demo/demo_337
python main.py                    # serial
mpirun -n <N> python main.py      # parallel

# mesh and reference data (outside AFSI, in the pulse container)
cd data/plot && docker compose up -d
docker exec -it fenicsx-pulse-container /usr/bin/bash
cd /repo/plot
python generate_mesh.py           # -> ../mesh/lv_ellipsoid/geometry/
python bench-ilv-inflation.py     # -> ../reference/diastole-pulse-disp.txt
python bench-ilv-contraction.py   # -> ../reference/systole-pulse-disp.txt
python middle_wall_location.py    # -> ../reference/ideal_middle_wall.txt
```

## References

{{< color "red" >}}TODO: references — add Land et al. (2015) Problem 2, the pulse-fenicsx reference and the IBAMR comparison source.{{< /color >}}
