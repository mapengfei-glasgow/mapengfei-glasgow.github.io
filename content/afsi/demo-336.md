---
title: "demo_336 — disc carried by a lid-driven cavity"
description: "demo_336: a 2-D disc in a lid-driven cavity, run three ways — immersed-boundary finite elements, rigid multi-direct forcing, and an inertial elastic solid."
date: 2026-09-12
weight: 336
academic: true
---

## 1. What it is

A closed square cavity with a sliding lid carries a circular disc around its
primary vortex. The same case is implemented with three different couplings:

| Variant | Directory | Solid |
|---|---|---|
| Immersed-boundary finite elements | `fsi_paralell.py` | elastic disc, $\mathbf{P} = \mu_s(\mathbf{F} - \mathbf{F}^{-\mathrm{T}})$ |
| Rigid multi-direct forcing | `multi-direct-frocing/` | rigid disc, iterated direct forcing, no constitutive law |
| Elastic multi-direct forcing | `multi-direct-frocing-elastic/` | inertial disc, neo-Hookean + Kelvin–Voigt, added-mass term |

The point of the pair in `multi-direct-frocing*` is the back-effect question: a
light, soft body carried by the flow produces almost no reaction force on the
fluid, and the demonstration quantifies that against a solid-free reference.

## 2. Configuration

<p class="tcaption">Table 1. Common configuration. The cavity must start at the origin: the IBM kernel computes its base node as $X/h$ without subtracting a domain offset.</p>

| Quantity | Code name | Value |
|---|---|---|
| Cavity | `Lx`, `Ly` | $1.0 \times 1.0$ |
| Domain origin | `x0`, `y0` | $0.0$, $0.0$ (required) |
| Lid velocity | `U_lid` | $1.0$ |
| Density / viscosity | `rho`, `mu` | $1.0$ / $0.01$, i.e. $\mathrm{Re} = 100$ |
| Disc centre | `cx`, `cy` | $(0.6, 0.5)$ |
| Disc radius / diameter | `r`, `D` | $0.2$ / $0.4$ |
| Solid shear modulus (IB-FE) | `mu_s` | $0.1$ ($\lambda_s = 10$ hard-coded) |
| Penalty | `beta` | $1 \times 10^{8}$ |
| Velocity / force / pressure spaces | — | $\mathrm{P2}$ / $\mathrm{P2}$ / $\mathrm{P1}$ |

<p class="tcaption">Table 2. What differs between the three runs.</p>

| Variant | Fluid grid | $\Delta t$ | $T$ | Steps | Solid parameters |
|---|---|---|---|---|---|
| `fsi_paralell.py` | $64 \times 64$ | $1/200$ | $10.0$ | $2000$ | `mu_s` $= 0.1$, external mesh |
| `multi-direct-frocing` | $128 \times 128$ | $0.0025$ | $10.0$ | $4000$ | rigid, displacement field imposed |
| `multi-direct-frocing-elastic` | $128 \times 128$ | $0.0025$ | $1.0$ | $400$ | `mu_s` $= 0.05$, $\lambda_s = 0.5$, `mu_s_visc` $= 0.01$, `rho_s` $= 1.0$ |

The direct-forcing variants use a hand-written AB2 fractional step
($1.5/0.5$ convection, $n_{iter} = 10$ forcing iterations,
$\nabla^2 p = \frac{2}{3\Delta t}\nabla\cdot\mathbf{u}$, then
$\mathbf{u} \leftarrow \mathbf{u} - 1.5\Delta t\nabla p$) instead of
`ChorinSolver`. The elastic variant adds an implicit added-mass term
$\rho_f V_{node}$ to a lumped solid mass $M = \rho_s \pi r^2$ (row-sum lumping
of the consistent mass gives near-zero or negative vertex masses, hence the HRZ
lumping).

Environment overrides: `STEPS`, `NX`, `NY`, `DISK_MOTION` (`free`/`fixed`),
`MARKER_MODE` (`disk`/`boundary`) for `multi-direct-frocing`; `STEPS`, `DT`,
`NX`, `NY`, `RHO_S`, `MU_S`, `MU_S_VISC`, `LAMBDA_S`, `SOLID_ACTIVE`,
`OUTPUT_PATH` for the elastic variant; `T` for `run_ib_compare.py`.

## 3. Files

| File | Role |
|---|---|
| `fsi_paralell.py` | Immersed-boundary FE driver (`ChorinSolver`, elastic disc) |
| `multi-direct-frocing/` | Rigid-disc direct forcing: `configuration.py`, `main.py`, readme |
| `multi-direct-frocing-elastic/` | Inertial elastic disc: configuration, driver, readme, formula sheet (`direct_forcing_formulas.tex/.pdf`) |
| `run_ib_compare.py` | Offline harness: patches the network calls and the dolfinx-0.10 API break in `fsi_paralell.py`, then re-executes it |
| `ns.py`, `structral_force.py` | Superseded scratch scripts (no time loop / hard-coded absolute mesh path) |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_336/multi-direct-frocing
python main.py                 # 4000 steps, T = 10 s
DISK_MOTION=fixed python main.py

cd ../multi-direct-frocing-elastic
python main.py                 # 400 steps, T = 1 s
RHO_S=50 python main.py        # heavy solid: measurable back-effect
```

## 5. Results and notes

{{< figure src="/afsi/demo336-ib-vs-df.png" title="Figure 1. Archived comparison from `multi-direct-frocing-elastic/plot/compare_ib_df64.png`: centroid path, centroid $y(t)$ and top-edge $y(t)$ for the IB run and the direct-forcing runs at two resolutions." >}}

Numbers archived in the readmes rather than in result files:

| Quantity | Value | Source |
|---|---|---|
| Back-effect, no solid / soft ($\rho_s = 1$) / heavy ($\rho_s = 50$) | $u_{L2} = 0.0612$ / $0.0588$ / $0.0484$ at $t = 1.5$ s | `multi-direct-frocing-elastic/readme.md:112-116` |
| 10 s run, $64\times64$, $\mu_s = 0.2$ | full clockwise orbit, period $\approx 5$ s, top edge $0.993$, $\min \det\mathbf{F} > 0.7$ | `multi-direct-frocing-elastic/readme.md:103-106` |
| Solid viscosity comparison ($\rho_s = 1$, $\mu_s = 0.2$) | DF@128 without viscosity diverges at $t = 4.89$ s; with `mu_s_visc` $= 0.01$ top edge $0.993$ at $5$ s; IB@64 reaches only $0.980$ | `multi-direct-frocing-elastic/readme.md:143-148` |
| Rigid disc, $128\times128$, $t = 1.25$ s | centroid $(0.6,0.5) \to (0.48,0.485)$; $C_x \approx -0.78$ fixed vs $\approx -0.03$ free | `multi-direct-frocing/readme.md:88-94` |

Caveats worth carrying:

* `fsi_paralell.py` reads an external mesh from `~/afsi-data/336-lid-driven-disk/mesh/circle_20.xdmf`, which is not archived, and calls `create_vector(L_hat)`, which is invalid in dolfinx 0.10 — `run_ib_compare.py` patches both. The original IB route therefore does not run as shipped.
* Both direct-forcing variants are single-process only, require a grid aligned with the origin, and their drag/lift integrals are order-of-magnitude references only: the marker volumes sum to $\Delta s \cdot h \propto h$, so $\int \mathbf{f}_{\mathrm{IB}}\,\mathrm{d}V$ does not converge under refinement.
* The three drivers log to SwanLab and one queries `counter.pengfeima.cn`; `run_ib_compare.py` exists precisely to run them offline.
* `compare_ib_df64.png` and `visc_compare.png` are not referenced by any script (`visc_compare.png` also renders its Chinese labels as missing-glyph boxes), so their provenance is unclear — only `df64_10s.png` is cited by the readme.
