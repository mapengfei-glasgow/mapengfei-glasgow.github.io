---
title: "AFSI"
description: "AFSI — an automated fluid–structure interaction solver on FEniCSx: notes on every demo in the repository, with configurations, results and caveats."
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

## Note: isotropic kernels and the divergence-free condition

The reference study this site compares against (Li et al. 2025,
arXiv:2412.15408) rests on a known property of regularized delta functions:
**isotropic kernels (IB, BS) do not generally produce continuously
divergence-free interpolants**, even from discretely divergence-free velocity
fields, so an immersed structure can lose its incompressibility — most
visibly for closed, pressurised membranes. The paper's remedies are

* the **composite B-spline (CBS) kernels** — divergence-free interpolation by
  construction, no treatment needed — and
* for isotropic kernels, **volumetric stabilization**: a volumetric energy
  $U(J)$ modulated by a numerical Poisson ratio $\nu_S$, with
  $\kappa_S = 2G(1+\nu_S)/(3(1-2\nu_S))$ ($\nu_S = -1$ recovers $\kappa_S = 0$,
  i.e. no stabilization), together with modified invariants of the
  Cauchy–Green tensor.

The paper describes the stabilization as "consistency terms that vanish under
grid refinement" which "reduce spurious volume changes … while maintaining the
convergence properties of the underlying formulation"; without it,
"unphysical and sometimes extreme contractions of the immersed structure" can
occur. It also lists the costs, which this solver reproduces: volumetric
penalties "impose more severe time step restrictions for explicit timestepping
schemes", and the modifications "introduce additional isotropic stresses that
alter the pressure response".

In the AFSI demos here the fluid is a finite-element
($\mathbb{P}_2/\mathbb{P}_1$) solver coupled with the $\mathrm{IB}_4$ kernel
only: the discrete divergence-free property is **not** available, so the
effective incompressibility is carried by the material's volumetric term —
see the calibration in demo_443 §3 and the cross-check in demo_441 §4.3, and
the no-slip-box caveat of demo_442.

## The demo notes

One page per demo, all in the same paper-style layout — **setup → numerics →
results → discussion**. Anything still to be verified is marked in **red**;
`demo_423` and `demo_424` are complete, verified against closed-form or published
references. The tables below show the state of every demo.

### Two-dimensional

| Demo | Problem | State |
|---|---|---|
| [`demo_336`](/afsi/demo-336/) | Disc carried by a lid-driven cavity, three couplings (IB-FE, rigid and elastic direct forcing) | **Detailed study**: 6 configurations × 3 grids, per-step logs, trajectories, deformation and grid sensitivity |
| [`demo_339`](/afsi/demo-339/) | Flow past a cylinder, four ways (DFG 2D-3, $\mathrm{Re} = 100$) | **Detailed study**: grid/marker/iteration matrix, the drag integral shown to track the marker volume, and the wake shown to be steady rather than shedding |
| [`demo_340`](/afsi/demo-340/) | 2-D ideal valve, fibre-reinforced (FRH) leaflets at $45^\circ/60^\circ/75^\circ$ | Probe series archived and compared with Ryan et al. and Kamensky et al.; **full $T = 3$ s re-run** reproduced to $4\times10^{-4}$ |
| [`demo_343`](/afsi/demo-343/) | Two compliant discs transported through the ideal valve | **Live $t \le 0.2$ s run** at the shipped $320\times64$ resolution: leaflets open into a nozzle, discs carried downstream |
| [`demo_400`](/afsi/demo-400/) | Turtle outline under a periodic follower pressure | **Live $t \le 1$ s run**: physical four-lobe flow to $t\approx0.4$ s, then the explicit coupling diverges |
| [`demo_402`](/afsi/demo-402/) | Turek FSI2 — cylinder with a flexible flag | Configuration only; several readme/code conflicts flagged |
| [`demo_421`](/afsi/demo-421/) | Fish swimming around a circular tank (DFIBMFoam port) | IBM kernel origin bug documented; **live $T = 1$ s run** with the shed vortex pair and body path |
| [`demo_423`](/afsi/demo-423/) | Immersed anisotropic annulus at static equilibrium | **Full verification write-up** against the analytic pressure, now including the **executed refinement study** ($N = 16\ldots128$) |
| [`demo_424`](/afsi/demo-424/) | Tethered aorta, patent and occluded, in a box | **Full verification write-up**: refinement study and an IPCS solver defect |
| [`demo_441`](/afsi/demo-441/) | Cook's membrane, plane strain, in a modified 13 cm domain | **Runs done**: $\Delta Y = 0.625 \to 0.655$ cm for $M = 8 \to 16$, inside the reference band $0.59$–$0.68$ cm |
| [`demo_442`](/afsi/demo-442/) | Quasi-static pressurized circular membrane | **Runs done**: pressure jump within $1\,\%$ of $\kappa/R$; area error $\Delta A/A_0 = 1.3\times10^{-2}$ at $t=1$ s, four orders above the reference (FEM fluid background) |
| [`demo_443`](/afsi/demo-443/) | Compressed block under a central downward traction | **Runs done**: $\Delta Y = -4.10$ cm against the reference $-4.03$…$-4.09$ cm, after calibrating the material bulk modulus to restore the reference's effective incompressibility |

### Three-dimensional

| Demo | Problem | State |
|---|---|---|
| [`demo_337`](/afsi/demo-337/) | Idealised left ventricle under a physiological pressure load | MPI scaling tables and reference displacements archived |
| [`demo_341`](/afsi/demo-341/) | Sphere carried through a cubic cavity, NS against FSI | **Live 3-D run** at $GRID = 16$ to $t = 1$ s: PyVista scene, sphere trajectory and the three centreline profiles |
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

These pages are written in the shape of the
[FEniCSx tutorial](https://jsdokken.com/dolfinx-tutorial/chapter2/heat_equation.html):
the model problem and its weak form first, then the time-stepping scheme, then the
implementation quoted from the driver, and only then the results, the verification
and the cost. The upstream readmes in the AFSI repository are organised as file
manifests and configuration tables; where a page here reads like an audit rather than
a derivation, it is reporting what we measured rather than restating the code.
[`demo_340`](/afsi/demo-340/) is the worked example of the layout.

The field figures scattered through these pages come from two scripts:
`static/afsi/demo-fields-pyvista.py` (PyVista field panels for `demo_339`,
`demo_421` and `demo_423`) and `static/afsi/demo336-make_figures.py`,
`static/afsi/demo340-make_valve_figures.py` and `static/afsi/demo-figs-343-400.py`
for the other four. They read the
dolfinx XDMF/HDF5 with `xml.etree` + `h5py` because VTK's `XdmfReader` cannot open
this 2-D output in this environment — it reports
`XDMF Error ... Can't Open Dataset` and then the process dumps core — and hand the
mesh to `pyvista.UnstructuredGrid` for rendering.

Most demos accept environment-variable overrides — `STEPS`, `GRID`, `NX`/`NY`,
`CASE`, `SOLVER`, `CIRCLE` — so a case can be shortened for a quick check; each
page lists the ones that demo actually reads. Note that several drivers call
SwanLab (and one a counter service) on start-up, so offline runs need those calls
stubbed out; `demo_339/_short_run/run_compare.py` and `demo_336/run_ib_compare.py`
are examples that do exactly that.
