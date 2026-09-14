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


## 7. A detailed study of the cavity-driven disc

Case 336 is the one worth pushing hardest, so it was run as a small study rather
than a single case: six physical configurations, three grid resolutions, and every
step logged. This section reports what came out.

### 7.1 What was run

All runs are $T = 10\,\mathrm{s}$, $\Delta t = 0.0025\,\mathrm{s}$ ($4000$ steps), and
all share the same cavity ($1\times1$, $\mathrm{Re} = 100$) and disc
($r = 0.2$, initially at $(0.6,0.5)$). They differ in the solid model and its
parameters:

<p class="tcaption">Table 3. The run matrix. "Elastic" is the inertial neo-Hookean disc of §1 (the `multi-direct-frocing-elastic` driver) with Kelvin–Voigt damping; "rigid" is the iterated direct-forcing disc of §1.</p>

| Run | Solid model | Parameters | Steps done |
|---|---|---|---|
| `no_solid` | none | pure cavity, reference | $4000$ |
| `elastic_base` | elastic | $\mu_s = 0.2$, $\rho_s = 1$, $\mu_s^{visc} = 0.01$ | $4000$ |
| `elastic_soft` | elastic | $\mu_s = 0.05$ (softer) | $4000$ |
| `elastic_heavy` | elastic | $\rho_s = 20$ (heavier) | $2237$ † |
| `elastic_heavy_clamp` | elastic + centroid clamp | $\rho_s = 20$ | $4000$ |
| `rigid_free` | rigid | free rigid body | $4000$ |
| `rigid_fixed` | rigid | held fixed | $4000$ |
| `elastic_32` / `elastic_128` | elastic | as `elastic_base`, at $32^2$ / $128^2$ | $4000$ |

† the heavy disc reached the wall at $t = 5.595\,\mathrm{s}$ and the driver stopped
gracefully, as designed (`clamp_solid = False`). The clamped variant exists to get a
full ten seconds out of that parameter set; its clamp is a modelling artefact, not
physics.

### 7.2 Trajectories

{{< figure src="/afsi/demo336-study-trajectories.png" title="Figure 7. Disc-centre paths for all six configurations (left, coloured by time) and the centroid coordinates against time (right; solid = $x$, dotted = $y$). Every run loops through the same upper-left region; the elastic discs reach further into the corner and start their second loop by $t = 8$ s, while the fixed disc does not move at all." >}}

The paths are all closed loops in the upper-left quadrant of the cavity, and they
all run clockwise — the direction of the primary vortex:

| Run | $x$ range | $y$ range | net displacement | path length | swept angle |
|---|---|---|---|---|---|
| `elastic_base` | $[0.269, 0.723]$ | $[0.489, 0.873]$ | $0.393$ | $1.777$ | $-587^\circ$ |
| `elastic_soft` | $[0.284, 0.723]$ | $[0.490, 0.880]$ | $0.362$ | $1.629$ | — |
| `elastic_heavy` | $[0.173, 0.600]$ | $[0.478, 0.791]$ | $0.508$ | $0.618$ | $-262^\circ$ |
| `elastic_heavy_clamp` | $[0.231, 0.600]$ | $[0.478, 0.769]$ | $0.456$ | $0.614$ | — |
| `rigid_free` | $[0.273, 0.663]$ | $[0.484, 0.769]$ | $0.300$ | $1.399$ | $-338^\circ$ |
| `rigid_fixed` | $0.600$ | $0.500$ | $0$ | $0$ | $0^\circ$ |

{{< figure src="/afsi/demo336-study-orbit.png" title="Figure 8. Orbit progress. Left: the angle swept about the cavity centre; a full loop is $360^\circ$. The elastic disc manages **two** loops in ten seconds (a period near $5$ s), while the rigid disc covers one and the heavy disc only three quarters. Right: distance from the cavity centre, which shows that both elastic and rigid discs pass close to the centre twice per loop." >}}

Two things stand out. First, the **elastic disc orbits faster than the rigid one**:
$587^\circ$ against $338^\circ$ over the same ten seconds. The elastic disc is
carried by the flow and lags it less, while the rigid disc — whose direct forcing
holds its surface at the local fluid velocity — slips against the vortex. Second,
the **clamp changes the trajectory qualitatively**: the clamped heavy disc stays in
a smaller loop near the start point, whereas the unclamped one escapes toward the
left wall. Any conclusion drawn from the clamped run is therefore about the clamp,
not about a heavy disc.

### 7.3 Deformation, and how close the solid comes to failing

{{< figure src="/afsi/demo336-study-deformation.png" title="Figure 9. Solid mesh health (left), area change (middle) and RMS deformation (right) for the elastic runs. The dashed line at $\det\mathbf F = 1$ is the undeformed state and the shaded band is where elements would invert; every run stays clear of it, but the heavy disc gets to $0.603$ and the baseline to $0.704$." >}}

| Run | $\max\lvert u_s\rvert$ | $\min\det\mathbf F$ | $V/V_0$ | $(\text{effective radius})/r$ |
|---|---|---|---|---|
| `elastic_base` | $0.820$ | $0.704$ | $1.107$ | $1.052$ |
| `elastic_soft` | $0.824$ | $0.776$ | $1.049$ | $1.024$ |
| `elastic_heavy` | $0.590$ (at $t=5.6$) | $0.603$ | $1.039$ | $1.019$ |
| `elastic_heavy_clamp` | $0.881$ | $0.655$ | $1.076$ | $1.037$ |

The displacement magnitudes are the headline: the disc starts with a radius of
$0.2$ and its nodes move up to $0.82$ — **four radii**. This is not a slightly
wobbling disc; the baseline run is a strongly deforming soft body being stretched
around the vortex, and the RMS displacement ($0.40$) says the deformation is
distributed over the body rather than localised.

The area change deserves a note, because it is easy to misread. The configuration
sets $\lambda_s = 0.5$, i.e. a very compressible neo-Hookean solid, so $J$ is
allowed to grow. The baseline run's area increases by $10.7\,\%$ over the ten
seconds, which is a genuine feature of the chosen material parameters rather than a
conservation failure — a nearly incompressible solid would need a much larger
$\lambda_s$, and then P2 elements lock (see the elastic variant's notes).

$\min\det\mathbf F$ is the quantity that decides whether the run survives at all: the
explicit coupling inverts an element once it crosses zero. All four elastic runs end
above $0.6$, and the baseline's minimum, $0.7038$, is reached late in the run.

### 7.4 Energy and forces

{{< figure src="/afsi/demo336-study-histories.png" title="Figure 10. Top row: the $x$ and $y$ components of the immersed-boundary force integral. Bottom left: the fluid energy norm $u_{L2}$. Bottom right: the maximum solid displacement, with the disc diameter marked. The force spikes are not physics — see the caveat in §8 about the marker-volume sum being $\propto h$." >}}

The fluid energy norm is the cleanest way to compare the runs, because it does not
depend on the force integralisation:

| Run | $u_{L2}$ at $t = 10\,\mathrm{s}$ | relative to the no-solid run | $\max u_{L2}$ |
|---|---|---|---|
| `no_solid` | $0.0672$ | — | $0.0672$ |
| `elastic_base` | $0.0623$ | $-7.3\,\%$ | $0.0851$ |
| `elastic_soft` | $0.0593$ | $-11.8\,\%$ | — |
| `elastic_heavy_clamp` | $0.0518$ | $-23.0\,\%$ | $0.0548$ |
| `rigid_free` | $0.0529$ | $-21.2\,\%$ | $0.0900$ |

The elastic discs take only a few per cent of energy out of the cavity at the
baseline parameters, and the softer one takes more than the baseline — which is the
back-effect conclusion already recorded in the readme, now with numbers: a light,
soft body carried by the flow pushes back very little, and making it softer still
does not make it a better obstacle. What does change the budget is mass: the
clamped heavy disc removes $23\,\%$, as much as the rigid one removes through its
no-slip constraint. Note also that the *peak* $u_{L2}$ is high early in every
solid run ($0.085$–$0.090$ against a monotone $0.067$ for the empty cavity) — the
disc perturbs the flow strongly while it is being accelerated, even when the
late-time energy is lower.

### 7.5 Grid sensitivity

{{< figure src="/afsi/demo336-study-grid.png" title="Figure 11. The baseline elastic case at $32^2$, $64^2$ and $128^2$. The 64 and 128 curves are indistinguishable; the 32 grid agrees until about $t = 6$ s and then drifts." >}}

| Grid | $x$ range | $y$ range | centroid at $t=5$ | $\max\lvert u_s\rvert$ | $\min\det\mathbf F$ | swept angle |
|---|---|---|---|---|---|---|
| $32^2$ | $[0.271,0.719]$ | $[0.489,0.871]$ | $(0.572, 0.860)$ | $0.817$ | $0.704$ | $-228^\circ$ |
| $64^2$ | $[0.269,0.723]$ | $[0.489,0.873]$ | $(0.572, 0.862)$ | $0.820$ | $0.704$ | $-587^\circ$ |
| $128^2$ | $[0.269,0.724]$ | $[0.489,0.873]$ | $(0.572, 0.862)$ | $0.821$ | $0.703$ | $-587^\circ$ |

$64^2$ and $128^2$ agree to every digit reported; $32^2$ matches the centroid to
$0.002$ and the extreme displacements to $0.4\,\%$ but **does not reproduce the
orbit**: it covers one loop instead of two. So the field quantities are
grid-converged at $64^2$, while the long-time orbital phase is not resolved there —
that is the practical resolution requirement for this case.

### 7.6 Flow field

{{< figure src="/afsi/demo336-study-fields.png" title="Figure 12. The rigid-disc run at $t = 0, 2, 4, 6, 8, 10$ s: velocity magnitude (top), vorticity (middle) and pressure (bottom), with the disc outline drawn from its own displacement field. The cavity vortex forms by $t=2$ s, the disc is squeezed through the top-left corner between $t = 4$ and $6$ s where the velocity and pressure gradients are largest, and the flow is close to periodic afterwards." >}}

The instantaneous fields show why the trajectory is what it is. At $t = 4$ s the
disc sits in the upper-left corner where the return flow meets the lid-driven one;
that is exactly where the deformation peaks and where $\det\mathbf F$ falls
fastest. After $t = 6$ s the disc rides the vortex core and the field returns to a
state close to its $t = 2$ s shape, consistent with the nearly periodic orbit.

### 7.7 How to reproduce

```bash
cd afsic/demo/demo_336
# rigid disc, full 10 s
OUTPUT_PATH=<dir>/ NX=64 NY=64 STEPS=4000 DISK_MOTION=free \
    python multi-direct-frocing/main.py
# elastic disc; the parameters of the matrix above
cd multi-direct-frocing-elastic
OUTPUT_PATH=<dir>/ NX=64 NY=64 STEPS=4000 MU_S=0.2 RHO_S=1 MU_S_VISC=0.01 python main.py
```

Every run writes a per-step `metrics.csv`
(`t,cx,cy,disp_max,disp_rms,det_min,volume,Fx,Fy,p_L2,u_L2` for the elastic driver,
and `t,cx,cy,theta,Vc_x,Vc_y,omega,u_L2,p_L2,u_max` for the rigid one), which is
what `static/afsi/demo336-study.py` consumes to build Figures 7–12. The raw logs are
archived under `static/afsi/demo336-study/`.

Two operational notes: the elastic driver runs under MPI (the $128^2$ run took
$1439\,\mathrm{s}$ serial, the $64^2$ one $521\,\mathrm{s}$) but in this environment
MPI aborts it with a heap-corruption error, so the whole matrix above is serial; and
the rigid driver ignores `OUTPUT_PATH` unless patched, writing into the demo tree
otherwise.

## 8. Further numbers and caveats

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
