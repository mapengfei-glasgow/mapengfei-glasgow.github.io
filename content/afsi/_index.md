---
title: "AFSI"
description: "AFSI — an automated fluid–structure interaction solver on FEniCSx: notes on every demo in the repository, with configurations, run commands, results and caveats."
date: 2026-09-12
academic: true
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

## The demo notes

One page per demo in `afsic/demo`, written from the sources: the parameter set as
the code actually runs it, the files and their roles, the commands, whatever
results are archived, and the discrepancies that would otherwise cost an
afternoon. Where nothing is archived, the page says so rather than quoting the
readme.

Two demos are worked through in full, against closed-form or published
references — `demo_423` and `demo_424` below; those pages carry the measured
errors, refinement orders and figures.

### Two-dimensional

| Demo | Problem | State |
|---|---|---|
| [`demo_336`](/afsi/demo-336/) | Disc carried by a lid-driven cavity, three couplings (IB-FE, rigid and elastic direct forcing) | Back-effect and viscosity-comparison tables recorded; two result figures |
| [`demo_339`](/afsi/demo-339/) | Flow past a cylinder, four ways (DFG 2D-3, $\mathrm{Re} = 100$) | Short-run comparison archived; drag-coefficient grid-dependence study |
| [`demo_340`](/afsi/demo-340/) | 2-D ideal valve, fibre-reinforced (FRH) leaflets at $45^\circ/60^\circ/75^\circ$ | Probe series archived and compared with Ryan et al. and Kamensky et al. |
| [`demo_343`](/afsi/demo-343/) | Two compliant discs transported through the ideal valve | Configuration only; no results archived |
| [`demo_400`](/afsi/demo-400/) | Turtle outline under a periodic follower pressure | Configuration only; inlet condition and geometry files need attention |
| [`demo_402`](/afsi/demo-402/) | Turek FSI2 — cylinder with a flexible flag | Configuration only; several readme/code conflicts flagged |
| [`demo_421`](/afsi/demo-421/) | Fish swimming around a circular tank (DFIBMFoam port) | Configuration only; the IBM kernel origin bug is documented |
| [`demo_423`](/afsi/demo-423/) | Immersed anisotropic annulus at static equilibrium | **Full verification write-up** against the analytic pressure |
| [`demo_424`](/afsi/demo-424/) | Tethered aorta, patent and occluded, in a box | **Full verification write-up**: refinement study and an IPCS solver defect |

### Three-dimensional

| Demo | Problem | State |
|---|---|---|
| [`demo_337`](/afsi/demo-337/) | Idealised left ventricle under a physiological pressure load | MPI scaling tables and reference displacements archived |
| [`demo_341`](/afsi/demo-341/) | Sphere carried through a cubic cavity, NS against FSI | Configuration only; inlet/wall marking needs checking |
| [`demo_401`](/afsi/demo-401/) | Sperm-cell solid geometry and mesh | Pre-processing only — no solver in the directory |
| [`demo_403`](/afsi/demo-403/) | Elastic plate in cross flow (Tuković §4.5) | Configuration only; the `plot/` artefacts belong to the 2-D valve |
| [`demo_405`](/afsi/demo-405/) | Vessel-wall FSI with merged leaflets | Configuration only; meshes and the pressure model are missing |

## Running a demo

AFSI needs FEniCSx 0.10.0 and an editable install of the `afsic` package:

```bash
sudo install/install_env.sh
source install/activate_dolfinx
install/install_dolfinx
cd afsic && pip install .

cd afsic/demo/demo_424
CASE=open NY=45 python generate_mesh.py && CASE=open NY=45 python main.py
```

Most demos accept environment-variable overrides — `STEPS`, `GRID`, `NX`/`NY`,
`CASE`, `SOLVER`, `CIRCLE` — so a case can be shortened for a quick check; each
page lists the ones that demo actually reads. Note that several drivers call
SwanLab (and one a counter service) on start-up, so offline runs need those calls
stubbed out; `demo_339/_short_run/run_compare.py` and `demo_336/run_ib_compare.py`
are examples that do exactly that.
