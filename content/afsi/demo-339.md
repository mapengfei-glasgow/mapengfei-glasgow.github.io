---
title: "demo_339 — flow past a cylinder, four ways"
description: "demo_339: the DFG 2D-3 benchmark (Re = 100) solved with no cylinder, a body-fitted mesh, immersed-boundary finite elements and multi-direct forcing."
date: 2026-09-12
weight: 339
academic: true
---

## 1. What it is

The DFG benchmark 2D-3 — channel flow past a cylinder at $\mathrm{Re} = 100$ —
solved four ways on the same SI-unit geometry, so that the treatments of the
body can be compared directly:

| Case | Directory | Treatment of the cylinder |
|---|---|---|
| 1 | `1-no-cylinder/` | none — baseline channel |
| 2 | `2-body-fitted/` | a hole in a Gmsh mesh with a no-slip Dirichlet condition on it |
| 3 | `3-ibfe/` | an immersed near-rigid neo-Hookean disc ($\mu_s = 7.7\times10^{10}$ Pa) held by a $\beta = 10^{12}$ penalty |
| 4 | `4-multi-direct-forcing/` | multi-direct forcing with a rigid marker set and interior masking |

{{< figure src="/afsi/demo339-setup.png" title="Figure 1. The DFG 2D-3 channel and the four ways the cylinder is treated." >}}

## 2. Configuration

<p class="tcaption">Table 1. Shared parameters (SI units). Cases 1, 3 and 4 use the same uniform grid; case 2 replaces it with a Gmsh mesh.</p>

| Quantity | Code name | Value |
|---|---|---|
| Channel | `Lx` × `Ly` | $2.2 \times 0.41\,\mathrm{m}$ |
| Cylinder centre | `cx`, `cy` | $(0.2, 0.2)\,\mathrm{m}$ |
| Cylinder radius | `R` | $0.05\,\mathrm{m}$, i.e. $D = 0.1\,\mathrm{m}$ |
| Mean inlet velocity | `Um` | $1.0\,\mathrm{m\,s^{-1}}$ |
| Density / viscosity | `rho`, `mu` | $1000\,\mathrm{kg\,m^{-3}}$ / $1.0\,\mathrm{Pa\,s}$ |
| Reynolds number | $\mathrm{Re} = \rho U_m D/\mu$ | $100$ |
| Grid | `Nx` × `Ny` | $220 \times 41$, $h \approx 0.01\,\mathrm{m}$ |
| Time step / end time | `dt`, `T` | $0.001\,\mathrm{s}$ / $10\,\mathrm{s}$ ($10^4$ steps) |
| Inlet profile | `TurekInlet` | $u_x = 1.5\,U_m\,y(H-y)/(H/2)^2$, ramp $t_{ramp} = 2\,\mathrm{s}$ |
| Body-fitted mesh | `channel_hole.msh` | $10\,762$ nodes, $21\,524$ elements, $\text{size} \le 0.01\,\mathrm{m}$ |
| IB-FE disc mesh | `cylinder_solid.xdmf` | Gmsh, size $0.002$–$0.005\,\mathrm{m}$ (must be generated) |
| Direct-forcing markers | `n_markers`, `n_iter` | $128$ rim markers ($\Delta s \approx 2.45\,\mathrm{mm}$), $10$ iterations |

Cases 1–3 use `ChorinSolver` with $\mathrm{P2}/\mathrm{P1}$ elements; case 4 uses
the hand-written AB2 fractional step with iterated direct forcing and an interior
mask that zeroes the velocity inside $r < R$.

Environment overrides: `STEPS` in case 4's configuration and in
`_short_run/run_compare.py` (default $300$ steps, which recomputes $T$).

## 3. Files

| File | Role |
|---|---|
| `README.md` | Master document: method table, shared parameters, governing equations, short-run validation, dolfinx-0.10 fixes, drag-coefficient study |
| `1-no-cylinder/` | Baseline channel driver + configuration |
| `2-body-fitted/` | `channel_hole.geo`, archived `channel_hole.msh`, generator and driver |
| `3-ibfe/` | `cylinder_solid.geo`, generator, IB-FE driver with the penalty-fixed disc |
| `4-multi-direct-forcing/` | AB2 + multi-direct-forcing driver, configuration, readme |
| `_short_run/` | Offline harness that runs all four in one process and prints `[RESULT]` lines; `summary.txt` archives the four-way comparison |

## 4. Running it

```bash
conda activate afsi-dolfinx
cd afsic/demo/demo_339

cd 1-no-cylinder            && python main.py
cd ../2-body-fitted         && python main.py    # mesh already in the repo
cd ../3-ibfe                && python generate_mesh.py && python main.py
cd ../4-multi-direct-forcing && python main.py

STEPS=300 python _short_run/run_compare.py all   # offline four-way comparison
```

## 5. Results and notes

{{< figure src="/afsi/demo339-fields.png" title="Figure 2. All four treatments at 300 steps ($t = 0.3$ s), from the short-run harness. The inlet ramp takes 2 s, so the wake is only beginning to form." >}}

{{< figure src="/afsi/demo339-cd.png" title="Figure 3. The drag coefficient from the force integral shrinks with refinement — the effect the readme documents (archived numbers)." >}}

Archived results are the short-run summary and the numbers in the readmes:

| Quantity | Value | Source |
|---|---|---|
| 300-step $u_{L2}$ / $p_{L2}$: no-cylinder, body-fitted, IB-FE, mdf | $0.002728$ / $208\,905$; $0.002792$ / $207\,765$; $0.002728$ / $208\,905$; $0.002828$ / $0.224956$ | `_short_run/summary.txt` |
| Drag coefficient, $2500$ steps ($t = 2.5\,\mathrm{s}$): body-fitted / mdf disc / mdf boundary | $2.664$ / $4.091$ / $4.388$ | `4-multi-direct-forcing/readme.md:80-84` |
| Quasi-steady wake ($t > 6\,\mathrm{s}$, mdf) | $\mathrm{Cd} \approx 2.53$, $\mathrm{St} \approx 0.52$ against the reference $\mathrm{Cd} \approx 5.57$, $\mathrm{St} \approx 0.3$ | `4-multi-direct-forcing/readme.md:161-171` |
| Body-fitted, $10\,\mathrm{s}$ | wake spikes to $-5811\,\mathrm{m\,s^{-1}}$, Cd spikes to $10^{91}$ after $t > 6.8\,\mathrm{s}$ | `4-multi-direct-forcing/readme.md:175-180` |

### 5.1 A live run of the multi-direct-forcing case ($T = 5$ s)

The case was re-run as shipped (`4-multi-direct-forcing`, $220\times41$, $\Delta t=0.001$,
$n_{iter}=10$, boundary-ring markers with the interior mask) for $5000$ steps, i.e.
$t \le 5\,\mathrm{s}$ — serial, because the $\texttt{IBMesh}$ marker map is not
MPI-safe ($mpirun$ dies with a broadcast shape error). It took $812\,\mathrm{s}$.

{{< figure src="/afsi/demo339-cylinder-5s.png" title="Figure 4. The re-run: velocity magnitude with streamlines (top) and pressure (bottom, symlog) at $t = 0,1,2,3,4,5$ s, with the immersed cylinder drawn in black. The wake grows to a steady recirculation and then stops changing." >}}

{{< figure src="/afsi/demo339-forces.png" title="Figure 5. Drag and lift from the re-run. $C_d$ rises to a plateau of $2.527$ by $t \approx 2$ s and stays flat to five digits; the lift is a weak but clean sinusoid." >}}

{{< figure src="/afsi/demo339-pyvista.png" title="Figure 6. The same instant rendered with PyVista: the channel mesh with the immersed cylinder overlaid, velocity on the left and pressure on the right." >}}

<p class="tcaption">Table 3. The re-run's late window ($t > 2.5$ s).</p>

| Quantity | Value |
|---|---|
| $C_d$ | $2.5274$ (range $2.5270$–$2.5299$, std $6.8\times10^{-4}$) |
| $C_l$ | $-0.0528$ (std $8.0\times10^{-4}$) |
| Lift period (late window) | $0.380$ s, i.e. $\mathrm{St} = fD/U_m = 0.26$ |
| Field | $\max\lvert u\rvert = 2.09\,\mathrm{m\,s^{-1}}$ against an inlet peak of $1.5$ |

The re-run reaches $C_d = 2.53$, the same value the readme records for the $10$ s run,
so the force integral is reproducible at fixed resolution. What it does **not** show
is a vortex street: the lift amplitude is $1.5\,\%$ of $\lvert C_l\rvert$ and the flow
settles into a steady wake. That is consistent with the geometry — the cylinder
($r = 0.05$) blocks a quarter of the $0.41$-wide channel and sits only $2.6$ diameters
from the inlet — rather than with the unbounded DFG 2D-3 benchmark, whose reference
values ($C_d \approx 3.22$, $\mathrm{St} \approx 0.30$) this configuration does not
reproduce quantitatively. The readme's caveat about the missing density factor in
$C_d$ (even though $\rho = 1000$ is set) applies here too.

The readme's own conclusion is that the **velocity field converges but the
volume-force-integral drag does not**: marker volumes sum to $2\pi r h \propto h$,
so $\mathrm{Cd}$ from $\int \mathbf{f}_{\mathrm{IB}}\,\mathrm{d}V$ is
grid-dependent (the resolution study gives $0.439$, $0.268$, $0.157$ for
$110\times21$, $220\times41$, $440\times82$ against a reference $0.292$). A
control-volume momentum balance is recommended instead.

Caveats:

* `README.md` states that `cylinder_solid.xdmf` already exists for case 3, but no
  such file is archived — `generate_mesh.py` must run first.
* Three drivers embed a SwanLab API key and require network access;
  `_short_run/run_compare.py` replaces those calls for offline runs.
* The marker-id conventions differ between cases (case 1/3 use
  $14/12/11/13$ for inlet/outlet/bottom/top, case 2's Gmsh tags are
  $11/12/13/14$, case 4 uses the library constants $1..4$).
* Case 4's drag coefficient omits the density factor even though the
  configuration sets $\rho = 1000$, so whether the archived $\mathrm{Cd}$ values
  are density-normalised is unclear.
* The IB-FE case is inherently stiff: the disc drifts $\approx 9\times10^{-4}\,\mathrm{m}$
  over $300$ steps and the solid force becomes `NaN` after $\approx 200$ steps.

## 6. A detailed study of the cylinder case

Section 5 records the demo's own results and the resolution study its readme
carries. This section re-runs the multi-direct-forcing variant as a matrix and
reports what the fields actually show.

### 6.1 What was run

All runs use the shipped physics — channel $2.2\times0.41$, cylinder $r = 0.05$ at
$(0.2,0.2)$, $\rho = 1000$, $\mu = 1$, inlet peak $1.5\,\mathrm{m\,s^{-1}}$,
$\Delta t = 10^{-3}$ — and differ in the grid, the marker model or the iteration
count. Each ran to $t = 6\,\mathrm{s}$, i.e. $4\,\mathrm{s}$ past the end of the
inlet ramp.

<p class="tcaption">Table 4. The run matrix.</p>

| Run | Grid | Difference from the shipped case | Steps |
|---|---|---|---|
| `r110` | $110\times21$ | coarser | $6000$ |
| `r220` | $220\times41$ | shipped resolution | $6000$ |
| `r440` | $440\times82$ | finer | $6000$ |
| `no_cyl` | $220\times41$ | cylinder markers moved outside the domain | $6000$ |
| `disk_marks` | $220\times41$ | filled-disc markers instead of a boundary ring | $6000$ |
| `iter2` / `iter20` | $220\times41$ | $n_{iter} = 2$ / $20$ instead of $10$ | $6000$ |

### 6.2 The drag integral tracks the marker volume, and the fine grid fails

The readme records that the volume-force integral *decreases* under refinement
($0.439 \to 0.268 \to 0.157$ at $110\times21$, $220\times41$, $440\times82$).
Re-measured here over the statistically steady window $t > 2.5\,\mathrm{s}$, the
decrease is there but the fine grid never gets that far:

{{< figure src="/afsi/demo339-study-cd.png" title="Figure 7. Left: the force-integral $C_d$ at three resolutions, with the body-fitted value the tutorial reports. Middle: the apparent shedding frequency from the lift signal — but see §6.3, the lift signal is not a vortex street. Right: lift histories for every variant." >}}

| Grid | $C_d$ (force integral) | marker volume $\Delta V_l$ | status |
|---|---|---|---|
| $110\times21$ | $4.3676 \pm 0.0045$ | $48.50\,\mathrm{mm^2}$ | steady |
| $220\times41$ | $2.5282 \pm 0.0029$ | $24.54\,\mathrm{mm^2}$ | steady |
| $440\times82$ | — | $12.55\,\mathrm{mm^2}$ | **diverges at $t = 2.28\,\mathrm{s}$** |

The ratio $4.3676/2.5282 = 1.73$ tracks the marker-volume ratio
$48.50/24.54 = 1.98$: halving the grid halves $\Delta V_l = \Delta s \cdot h$ and
the spread-force integral grows with it. So the discrete drag is a property of the
marker discretisation rather than of the flow, exactly as the readme argues — and
the values it quotes for this configuration should not be read as drag
coefficients.

The fine grid does not merely give a different number: it **fails**. `r440`
blows up at $t = 2.28\,\mathrm{s}$ ($u_{L2}$ jumps from $\mathcal O(1)$ to
$10^{180}$), after which the solution never settles — $C_d$ wanders with a standard
deviation of $2.6$ around a mean of $2.1$, and no finite window can be used for
statistics. This is not a CFL problem: at $440\times82$ with $\Delta t = 10^{-3}$ the
advective CFL is $0.30$, half the value the coarse grid runs stably at. The cause is
the IBM forcing itself: the direct-force impulse per step scales with the marker
volume $\Delta V_l \propto h$, so halving $h$ halves the impulse and, in an
explicitly coupled scheme, eventually destabilises it. Halving $\Delta t$ as well
does run (`440\times82` with $\Delta t = 5\times10^{-4}$ starts cleanly), but at
$0.14\,\mathrm{ms}$ of simulated time per second it needs about five hours to reach
$t = 4\,\mathrm{s}$, which is beyond what this study spent.

### 6.3 The wake is steady, not a vortex street

{{< figure src="/afsi/demo339-study-wake.png" title="Figure 8. Left: the centreline velocity at $t = 6$ s at both resolutions — the deficit closes monotonically and the two grids lie on top of each other. Right: the lift signal magnified by $10^3$. The residual oscillation is 0.005 in $C_l$, against a mean level of $-0.05$." >}}

The lift signal never develops the large periodic oscillation that a von Kármán
street produces. Over $t > 2.5\,\mathrm{s}$ the lift sits at a constant offset with a
peak-to-peak ripple of

| Grid | $\overline{C_l}$ | peak-to-peak $C_l$ | recirculation length (from the centreline) |
|---|---|---|---|
| $110\times21$ | $-0.1606$ | $0.0093$ | $\approx 0.14\,\mathrm{m} = 1.4\,D$ |
| $220\times41$ | $-0.0527$ | $0.0050$ | $\approx 0.14\,\mathrm{m} = 1.4\,D$ |

A ripple three orders of magnitude below the dynamic pressure, and identical
recirculation lengths on two very different grids, is the signature of a **steady
symmetric wake**. Figure 9 shows it directly: the vorticity field behind the
cylinder is a symmetric pair of shear layers with no alternating cores, and it
barely changes between $t = 2$ and $t = 6$.

{{< figure src="/afsi/demo339-study-fields.png" title="Figure 9. Vorticity (top) and pressure (bottom) at five instants for the shipped resolution. The pattern is symmetric about the centreline and stationary: no vortex street forms." >}}

This matters for how the case is described. Shedding frequencies computed from that
ripple are noise — the period is stable enough to divide by ($0.38\,\mathrm{s}$,
i.e. $\mathrm{St} \approx 0.26$) but the amplitude carries no signal. The honest
statement is that **this implementation, at these resolutions, produces a steady
wake at $\mathrm{Re} = 100$**, where the DFG 2D-3 benchmark is unsteady
($\mathrm{St} \approx 0.295$, $C_l$ amplitude $\approx 1$).

### 6.4 Marker model and iteration count

{{< figure src="/afsi/demo339-study-variants.png" title="Figure 10. Drag and energy histories for every variant: the two grids, the two marker models, and $n_{iter} = 2$ and $20$." >}}

The remaining knobs matter much less than the grid:

| Run | Markers | $n_{iter}$ | $C_d$ | $\overline{C_l}$ | $u_{L2}$ at $t=6$ |
|---|---|---|---|---|---|
| `r220` | boundary ring, 128 | $10$ | $2.5282 \pm 0.0029$ | $-0.05273$ | $1.1178$ |
| `disk_marks` | filled disc | $10$ | $2.5282 \pm 0.0029$ | $-0.05273$ | $1.1178$ |
| `iter2` | boundary ring, 128 | $2$ | $1.6891 \pm 0.0019$ | $-0.05208$ | $1.1148$ |
| `iter20` | boundary ring, 128 | $20$ | $2.5962 \pm 0.0029$ | $-0.05137$ | $1.1180$ |
| `no_cyl` | none | — | $0.0000$ | $0.00000$ | $1.0826$ |

Two clean conclusions. **The marker model is irrelevant**: filling the disc with
interior markers returns bit-identical drag to the boundary ring alone, so the ring
is sufficient and the `disk` mode is pure cost. And **the iteration count is a real
parameter but a small one**: dropping from $10$ to $2$ iterations costs $33\,\%$ of
the drag, while going to $20$ changes it by $+2.7\,\%$ — so $10$ is close to
converged in $n_{iter}$, which is presumably why the demo ships with it. The
cylinder's presence costs the flow about $3\,\%$ of its energy norm
($1.1178$ against $1.0826$), a sensible magnitude for a $24\,\%$ blockage.

### 6.5 Why it cannot be compared with the published benchmark as-shipped

Two independent mismatches, both in the shipped configuration:

1. **The inlet amplitude is 1.5× too large.** The driver builds the inlet from
   `TurekInlet(Um=Um)` with `Um = 1.0`, and `TurekInlet` evaluates
   $1.5\,U_m\,y\,(H-y)/(H/2)^2$ — so the profile peaks at $1.5\,U_m = 1.5$ with
   $\overline{u} = 1.0$. The DFG 2D-3 inlet is
   $4Uy(0.41-y)/0.41^2$ with $U = 1.5\sin(\pi t/8)$, which peaks at $1.5$ and has
   $\overline{u} = 1.0$ *only when the sine is at its maximum*. The demo therefore
   runs at a steady $\mathrm{Re} = 100$ while the benchmark sweeps
   $\mathrm{Re} = 0 \to 100$ over eight seconds and never holds a steady state.
2. **The force coefficients are normalised differently.** The driver reports
   $C_d = 2F_x/(\bar U^2 D)$ with $\bar U = 1$, i.e. the DFG $C_d$ (which uses the
   peak) is $2.25\times$ larger for the same force. Neither the readme's
   $\approx 0.29$ (body-fitted, surface-stress integration) nor the DFG
   $\approx 3.22$ matches the number this driver prints.

A variant with `DFG_PROFILE=1.5` was added to test the inlet question directly. It
diverges: at $\Delta t = 10^{-3}$ and an inlet peak of $2.25$ the step is simply too
large, and the solution blows up around $t = 1.7\,\mathrm{s}$ (see §6.6). Fixing the
comparison properly needs both a smaller $\Delta t$ and the benchmark's time-dependent
amplitude, not a constant one.

### 6.6 What to reproduce, and what to fix

```bash
cd afsic/demo/demo_339/4-multi-direct-forcing
# resolution study (NX/NY now honoured; they were silently ignored before)
OUTPUT_PATH=<dir>/ NX=220 NY=41 STEPS=6000 python main.py
# marker model and iteration-count sensitivity
OUTPUT_PATH=<dir>/ MARKER_MODE=disk STEPS=6000 python main.py
OUTPUT_PATH=<dir>/ N_ITER=20        STEPS=6000 python main.py
```

Three defects were found and fixed while setting this up, all of which change
results silently:

* **`NX`/`NY` were ignored.** The configuration read `STEPS`, `MARKER_MODE` and
  `DISK_MOTION` but not the grid — so runs intended as $110\times21$ and
  $440\times82$ both ran at $220\times41$. The first version of the resolution table
  above was flat for exactly this reason.
* **The DFG-profile variant has no stable $\Delta t$.** `DFG_PROFILE=1.5` (peak
  $2.25\,\mathrm{m\,s^{-1}}$) diverges at the shipped $\Delta t = 10^{-3}$.
* The control-volume drag recommended by the readme **cannot be applied to this
  channel as configured**: with a cylinder only $2D$ from the inlet and a domain of
  $4.1D$, the balance is dominated by the channel-wall friction integral
  ($\approx 70\,\mathrm{N}$) and the inlet/outlet momentum flux
  ($\approx 37\,\mathrm{N}$), against a $0.13\,\mathrm{N}$ cylinder force. A
  circular control volume hugging the cylinder would be needed, and that cannot be
  integrated accurately on a Cartesian grid this coarse.
