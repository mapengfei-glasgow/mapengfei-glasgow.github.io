---
title: "demo_402 — Turek FSI2 benchmark (2-D)"
description: "demo_402: the Turek FSI2 channel-with-flag benchmark solved with immersed boundaries — configuration, and a careful note on where the shipped parameters differ from the published case."
date: 2026-09-12
weight: 402
academic: true
---

## 1. What it is

Channel flow past a circular cylinder that carries a flexible flag — the Turek
FSI2 benchmark — run through AFSI's immersed-boundary solver rather than a
body-fitted ALE mesh. The cylinder is not treated as rigid: it is the same
elastic material as the flag, held in place by a strong penalty. The readme is
explicit that this is a **qualitative replication, not a precision match**.

{{< figure src="/afsi/demo402-setup.png" title="Figure 1. The Turek FSI2 channel: the penalty-held cylinder and the flexible flag." >}}

## 2. Configuration

<p class="tcaption">Table 1. Parameters as the code actually runs them (`configuration.py`, CGS). The right-hand column records what the readme claims where the two disagree.</p>

| Quantity | Code name | Value (code) | Readme claim |
|---|---|---|---|
| Channel | `Lx`, `Ly` | $220 \times 41\,\mathrm{cm}$ | $2.5\,\mathrm{m}$ |
| Fluid cells | `Nx`, `Ny` | $220 \times 41$ (cell $1\,\mathrm{cm}$) | — |
| Density / viscosity | `rho`, `mu` | $1.0\,\mathrm{g\,cm^{-3}}$ / $10.0\,\mathrm{dyn\,s\,cm^{-2}}$ | $1000\,\mathrm{kg\,m^{-3}}$ / $1.0\,\mathrm{Pa\,s}$ |
| Mean inlet velocity | `Um` | $200\,\mathrm{cm\,s^{-1}}$ | $1.0\,\mathrm{m\,s^{-1}}$ |
| Reynolds number | — | $\approx 200$ (derived) | $100$ |
| Cylinder | `turek.geo` | $R = 0.05\,\mathrm{m}$ at $(0.2, 0.2)\,\mathrm{m}$, scaled $\times100$ in `main.py` | $D = 0.1\,\mathrm{m}$ |
| Flag | `turek.geo` | $0.35 \times 0.02\,\mathrm{m}$ | same |
| Solid law | `main.py:219-234` | compressible neo-Hookean, penalty `beta` $= 1\times10^{6}$ on cell tag $1$ | Saint Venant–Kirchhoff |
| Solid parameters | `mu_s`, `lambda_s`, `nu_s` | $2.0\times10^{7}$ / $8.0\times10^{7}\,\mathrm{dyn\,cm^{-2}}$, $\nu = 0.4$ | $E = 1.4\times10^{6}\,\mathrm{Pa}$, $\mu_s = 5\times10^{5}$ |
| Inlet ramp | `t_ramp` | $2.0\,\mathrm{s}$, cosine | same |
| Time step / end time | `dt`, `T` | $5\times10^{-5}\,\mathrm{s}$ / $10\,\mathrm{s}$ ($200\,000$ steps) | — |
| Solver | `ChorinSolver` | $\mathrm{CG2}$ / $\mathrm{CG1}$, force $\mathrm{CG2}$ | — |
| Output | `fps=100` | every $200$ steps | — |

There are **no environment overrides**; the demo has no `os.environ` lookup and
the solver is hard-coded to `ChorinSolver` regardless of the `nssolver` key.
`turek.geo` is in SI metres while everything else is in centimetres, and
`main.py` converts the solid with a two-line $\times100$ scaling — mixing the two
systems is the easiest way to break this case.

## 3. Files

| File | Role |
|---|---|
| `configuration.py` | Every parameter in one dict, plus `num_steps`, output path and experiment name |
| `turek.geo` | gmsh OpenCASCADE geometry: disk + flag, cut and fragmented so ball and tail share one conformal edge |
| `generate_mesh.py` | `turek.geo` → `turek_mesh.xdmf`/`.h5` with cell tags ($1$ ball, $2$ tail) and facet tag $3$ |
| `main.py` | IB-FSI driver: fluid, ramped parabolic inlet, neo-Hookean + penalty force, coupling, time loop |
| `readme.md` | Benchmark description, parameters, known limitations |

## 4. Running it

```bash
cd afsic/demo/demo_402
python generate_mesh.py    # turek.geo -> turek_mesh.xdmf/.h5 (not shipped)
python main.py             # or: mpirun -n <N> python main.py
```

## 5. Results and notes

**No results are archived**: the directory holds only the five source files,
`turek_mesh.xdmf` is not shipped, and the configured output root
`~/afsi-data/` does not exist here, so nothing from a run is stored. The readme
reports parameters, not measurements, and warns that a short run should be done
before committing to the full $200\,000$ steps.

Discrepancies to be aware of before quoting anything from this demo:

* **Stiffness**: the readme's $E = 1.4\times10^{6}\,\mathrm{Pa}$ with
  $\mu_s = 5\times10^{5}\,\mathrm{Pa}$ differs from the configured
  $\mu_s = 2\times10^{7}\,\mathrm{dyn\,cm^{-2}} = 2\times10^{6}\,\mathrm{Pa}$ by
  a factor of four; the code uses the configuration.
* **Flow rate**: the readme's $1\,\mathrm{m\,s^{-1}}$ / $\mathrm{Re} = 100$ does
  not match `Um` $= 2\,\mathrm{m\,s^{-1}}$, which puts the case at
  $\mathrm{Re} \approx 200$; the parent `demo/readme.md` repeats the stale claim.
* **Constitutive law**: the readme says Saint Venant–Kirchhoff; the assembled
  stress is neo-Hookean.
* **Physics that is not implemented**: the readme's gravity term
  ($g = 2\,\mathrm{m\,s^2}$ on the flag), its `cyl_stiffness_factor` and its
  `rho_s` do not appear anywhere in the code — the cylinder is held purely by the
  `beta` penalty.
* The logged `solid_force_norm` is $\int \mathbf{X}\cdot\mathbf{X}\,\mathrm{d}x$
  over the solid coordinates, not a force norm.
* The cylinder constraint is applied through the volume measure `dxx(1)` while
  the comments (and the commented-out `dss(3)` line) describe fixing the circle
  facet.
* Boundary markers are hard-coded ($14/12/11/13$) rather than taken from the
  package constants, and `IPCSSolver` is imported but never used.
* `main.py` needs SwanLab plus a remote counter call on rank $0$ before the
  simulation starts, so it does not run offline unchanged.
