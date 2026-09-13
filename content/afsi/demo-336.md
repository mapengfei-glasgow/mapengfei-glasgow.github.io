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

{{< figure src="/afsi/demo336-setup.png" title="Figure 1. The case: a square cavity with a sliding lid and a disc at $(0.6, 0.5)$." >}}

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

{{< figure src="/afsi/demo336-results.png" title="Figure 2. Smoke run at $48^2$ for 2 000 steps: the centroid path (barely moved at $t = 0.5$ s) and the drag coefficient; panel (c) is the back-effect table recorded in the readme." >}}

{{< figure src="/afsi/demo336-ib-vs-df.png" title="Figure 3. Archived comparison from `multi-direct-frocing-elastic/plot/compare_ib_df64.png`: centroid path, centroid $y(t)$ and top-edge $y(t)$ for the IB run and the direct-forcing runs at two resolutions." >}}

## 6. Snapshots at $t = 0, 2, 4, 6, 8, 10$ s

Both direct-forcing variants were re-run for the full $T = 10$ s on the $64^2$ grid
(the readme documents $64^2$ and $128^2$ as equivalent for the disc trajectory) and the
XDMF/HDF5 time series rendered with PyVista into the figures below. Nothing was restarted
from an interpolated state: $t = 0$ is the quiescent initial condition.

{{< figure src="/afsi/demo336-flow-pressure-0-10s.png" title="Figure 4. Rigid multi-direct forcing, 64x64. Top row: velocity magnitude with streamlines; bottom row: pressure with the time-averaged level removed (symlog colour scale, since the lid makes the corner values about ten times the interior signal). The disc interior is masked out; its outline is the deformed `disk.xdmf` geometry, reconstructed as reference circle plus displacement." >}}

At $t = 0$ the fluid is at rest and the pressure is still a smooth lid-corner field. By
$t = 2$ s the primary vortex is established and the disc — which started at $(0.6, 0.5)$ —
has been carried left to $(0.395, 0.514)$. The disc then climbs the left side
($t = 4$ s: $(0.276, 0.750)$), crosses under the lid ($t = 6$ s: $(0.568, 0.760)$, the
closest approach, still $\approx 4$ cm clear of the lid), descends the right side
($t = 8$ s: $(0.541, 0.518)$) and is swept back up in the return flow
($t = 10$ s: $(0.326, 0.621)$). The full loop, together with the direct-forcing force
coefficients and the disc's translational and angular speed, is in Figure 5.

{{< figure src="/afsi/demo336-history.png" title="Figure 5. Rigid run: disc-centre trajectory (dotted circle = initial position), the direct-forcing force coefficients $C_x$, $C_y$, $C_m$, and the rigid-body speeds. The coefficients are order-of-magnitude references only — the marker volume sums to $\Delta s \cdot h \propto h$, so $\int f_{\mathrm{IB}}\,\mathrm{d}V$ does not converge under refinement (see the caveats below)." >}}

{{< figure src="/afsi/demo336-solid-disc-0-10s.png" title="Figure 6. Rigid run: solid displacement $u_s$ on the deformed grid, true scale, initial disc dashed. The disc travels further than its own radius (max $\vert u_s \vert = 0.51$ against $r = 0.2$), so the field is contoured on the deformed mesh — at the reference positions only the small overlap with the current pose would show. The displacement is a rigid-body translation plus rotation about the initial centre, so the disc stays a circle and its radius is invariant (mean radius 0.1244 at every plotted time). The centroid reconstructed this way agrees with `disk_trace.csv` to 5e-7." >}}

For contrast, the elastic variant of the same case — an inertial neo-Hookean disc with
Kelvin–Voigt damping ($\mu_s = 0.2$, $\rho_s = 1$, `mu_s_visc` $= 0.01$, the parameter set
the readme documents for a 10 s run) — deforms strongly instead of translating rigidly:

{{< figure src="/afsi/demo336-elastic-solid-0-10s.png" title="Figure 7. Elastic run, 64x64, 4000 steps, $T = 10$ s. Top: $|u_s|$ on the reference mesh. Bottom: the deformed mesh itself, which shows the stretch and shear the soft disc accumulates in the cavity vortex. The dashed circle is the initial disc. $|u_s|$ peaks at 0.71 in the P1 output field (0.82 on the P2 solid space), and $\min \det \mathbf{F}$ stays above 0.70, so no element inverts." >}}

Raw history for both runs (the disc trace, the force coefficients, and the per-step
log) is archived under `static/afsi/demo336-run64/`; the full 400 MB XDMF/HDF5 field
output is not committed.

Both runs completed 4000 steps at $\Delta t = 0.0025$ s with no NaN and no wall contact;
the elastic run's solid stays well clear of inverting ($\min \det \mathbf{F} \ge 0.70$ over
the whole run). The snapshots were produced by `static/afsi/demo336-make_figures.py`,
which reads the `.xdmf`/`.h5` pair with `h5py` and `xml.etree` and draws the
streamlines with Matplotlib. VTK's `XdmfReader` cannot open this 2-D dolfinx output
(`XDMF Error ... Can't Open Dataset`, and the process then dumps core), and this
environment's `h5py`/`meshio` reject the HDF5 container as written
(`bad object header version number`) while the run is in flight, so the plotter reads the
finished `.h5` files directly.

## 7. Further numbers and caveats

Numbers archived in the readmes rather than in result files:

| Quantity | Value | Source |
|---|---|---|
| Back-effect, no solid / soft ($\rho_s = 1$) / heavy ($\rho_s = 50$) | $u_{L2} = 0.0612$ / $0.0588$ / $0.0484$ at $t = 1.5$ s | `multi-direct-frocing-elastic/readme.md:112-116` |
| 10 s run, $64\times64$, $\mu_s = 0.2$ | full clockwise orbit, period $\approx 5$ s, top edge $0.993$, $\min \det\mathbf{F} > 0.7$ | `multi-direct-frocing-elastic/readme.md:103-106` |
| Solid viscosity comparison ($\rho_s = 1$, $\mu_s = 0.2$) | DF@128 without viscosity diverges at $t = 4.89$ s; with `mu_s_visc` $= 0.01$ top edge $0.993$ at $5$ s; IB@64 reaches only $0.980$ | `multi-direct-frocing-elastic/readme.md:143-148` |
| Rigid disc, $128\times128$, $t = 1.25$ s | centroid $(0.6,0.5) \to (0.48,0.485)$; $C_x \approx -0.78$ fixed vs $\approx -0.03$ free | `multi-direct-frocing/readme.md:88-94` |

The re-runs behind Figures 4–7 add ($64 \times 64$, $\Delta t = 0.0025$ s, 4000 steps):

| Quantity | Value |
|---|---|
| Rigid disc, $T = 10$ s | centroid path $(0.600,0.500) \to (0.395,0.514) \to (0.276,0.750) \to (0.568,0.760) \to (0.541,0.518) \to (0.326,0.621)$; $|\mathbf{V}_c|_{\max} = 0.251$, $|\omega|_{\max} = 0.295$ rad/s, total rotation $1.055$ rad |
| Rigid disc, $T = 10$ s | $\max \vert u_s \vert = 0.509$ over the run; trajectories stay inside $x \in [0.273, 0.663]$, $y \in [0.484, 0.769]$; no wall contact |
| Rigid run fluid | $u_{L2}$ grows $0 \to 0.0529$; $\vert C_x \vert \le 1.07$, $\vert C_y \vert \le 2.04$ |
| Elastic disc, $T = 10$ s | $\max \vert u_s \vert = 0.820$ on the P2 solid space ($0.71$ in the P1 output field at the plotted times); peak at $t \approx 4$ s then partial rebound ($0.71 \to 0.61 \to 0.31 \to 0.44$); $\min \det \mathbf{F} = 0.7038 \ge 0.70$; volume $0.12566 \to 0.1274$; final centroid $(0.282, 0.732)$ |
| Elastic run fluid | $u_{L2} \to 0.0623$, i.e. above the rigid run's $0.0529$ and above the 1.5 s no-solid reference $0.0612$ |

Caveats worth carrying:

* `fsi_paralell.py` reads an external mesh from `~/afsi-data/336-lid-driven-disk/mesh/circle_20.xdmf`, which is not archived, and calls `create_vector(L_hat)`, which is invalid in dolfinx 0.10 — `run_ib_compare.py` patches both. The original IB route therefore does not run as shipped.
* Both direct-forcing variants are single-process only, require a grid aligned with the origin, and their drag/lift integrals are order-of-magnitude references only: the marker volumes sum to $\Delta s \cdot h \propto h$, so $\int \mathbf{f}_{\mathrm{IB}}\,\mathrm{d}V$ does not converge under refinement.
* The three drivers log to SwanLab and one queries `counter.pengfeima.cn`; `run_ib_compare.py` exists precisely to run them offline.
* `compare_ib_df64.png` and `visc_compare.png` are not referenced by any script (`visc_compare.png` also renders its Chinese labels as missing-glyph boxes), so their provenance is unclear — only `df64_10s.png` is cited by the readme.
